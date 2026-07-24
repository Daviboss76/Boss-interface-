import configparser
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from PyQt5.QtCore import QPoint, QSize, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def buscar_aplicativos():
  """Lê os arquivos .desktop do Linux para listar os apps instalados."""
  caminhos = [
      '/usr/share/applications/',
      os.path.expanduser('~/.local/share/applications/'),
  ]
  apps = []

  for caminho in caminhos:
    if os.path.exists(caminho):
      for arquivo in os.listdir(caminho):
        if arquivo.endswith('.desktop'):
          parser = configparser.ConfigParser(interpolation=None)
          try:
            parser.read(os.path.join(caminho, arquivo), encoding='utf-8')
            if 'Desktop Entry' in parser:
              entry = parser['Desktop Entry']
              if entry.getboolean('NoDisplay', fallback=False):
                continue
              nome = entry.get('Name', '')
              exec_cmd = entry.get('Exec', '')
              icone = entry.get('Icon', 'application-x-executable')
              if nome and exec_cmd:
                exec_limpo = (
                    exec_cmd.split('%')[0].strip() if '%' in exec_cmd else exec_cmd
                )
                apps.append(
                    {'nome': nome, 'exec': exec_limpo, 'icone': icone}
                )
          except Exception:
            pass
  return sorted(apps, key=lambda x: x['nome'])


class JanelaEnergia(QFrame):
  """Janela de confirmação de Energia compatível com Linux e Termux."""

  def __init__(self, parent=None):
    super().__init__(parent)
    self.initUI()

  def initUI(self):
    self.resize(360, 240)
    if self.parent():
      geo = self.parent().geometry()
      self.move(
          (geo.width() - self.width()) // 2, (geo.height() - self.height()) // 2
      )

    self.setStyleSheet("""
            QFrame {
                background-color: rgba(20, 20, 32, 240);
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 20px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 15);
                color: white;
                border-radius: 10px;
                padding: 10px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 30);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 40);
            }
        """)

    layout = QVBoxLayout(self)
    layout.setContentsMargins(20, 20, 20, 20)

    lbl_titulo = QLabel('⚡ Opções de Energia')
    lbl_titulo.setAlignment(Qt.AlignCenter)
    lbl_titulo.setFont(QFont('Ubuntu', 12, QFont.Weight.Bold))
    lbl_titulo.setStyleSheet(
        'color: white; border: none; background: transparent;'
    )
    layout.addWidget(lbl_titulo)

    layout.addSpacing(10)

    btn_desligar = QPushButton('🚪 Sair do Boss_OS')
    btn_desligar.setStyleSheet("""
            QPushButton { background-color: rgba(239, 68, 68, 0.4); border: 1px solid rgba(239, 68, 68, 0.6); }
            QPushButton:hover { background-color: rgba(239, 68, 68, 0.8); }
        """)
    btn_desligar.clicked.connect(self.exec_desligar)

    btn_reiniciar = QPushButton('🔄 Reiniciar Interface')
    btn_reiniciar.clicked.connect(self.exec_reiniciar)

    btn_cancelar = QPushButton('Cancelar')
    btn_cancelar.setStyleSheet('border: none; color: #a0aec0;')
    btn_cancelar.clicked.connect(self.close)

    layout.addWidget(btn_desligar)
    layout.addWidget(btn_reiniciar)
    layout.addWidget(btn_cancelar)

  def exec_desligar(self):
    if shutil.which('systemctl'):
      try:
        subprocess.run(['systemctl', 'poweroff'])
      except Exception:
        pass
    QApplication.quit()

  def exec_reiniciar(self):
    if shutil.which('systemctl'):
      try:
        subprocess.run(['systemctl', 'reboot'])
        QApplication.quit()
        return
      except Exception:
        pass
    os.execv(sys.executable, [sys.executable] + sys.argv)


class JanelaApp(QFrame):
  """Janela com movimentação suave e fluida estilo Ubuntu/Linux."""

  def __init__(self, titulo, comando, parent=None):
    super().__init__(parent)
    self.titulo_app = titulo
    self.comando = comando
    self.processo = None

    # Controle de arraste e estados
    self.arrastando = False
    self.drag_position = QPoint()
    self.maximizada = False
    self.geometria_antiga = None

    self.init_janela()
    self.executar_processo()

  def init_janela(self):
    self.resize(520, 340)
    self.move(120, 70)

    self.setStyleSheet("""
            QFrame#JanelaAppFrame {
                background-color: rgba(26, 27, 38, 240);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 12px;
            }
        """)
    self.setObjectName('JanelaAppFrame')

    layout_principal = QVBoxLayout(self)
    layout_principal.setContentsMargins(8, 6, 8, 8)

    # --- BARRA DE TÍTULO ---
    self.barra_titulo = QFrame(self)
    self.barra_titulo.setFixedHeight(36)
    self.barra_titulo.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 10);
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: none;
            }
        """)

    # Habilita o rastreamento dos eventos do mouse na barra de título
    self.barra_titulo.mousePressEvent = self.iniciar_arraste
    self.barra_titulo.mouseMoveEvent = self.mover_janela
    self.barra_titulo.mouseReleaseEvent = self.parar_arraste

    layout_barra = QHBoxLayout(self.barra_titulo)
    layout_barra.setContentsMargins(10, 0, 5, 0)

    lbl_titulo = QLabel(self.titulo_app)
    lbl_titulo.setFont(QFont('Ubuntu', 10, QFont.Weight.Bold))
    lbl_titulo.setStyleSheet('color: #f1f5f9; background: transparent;')
    layout_barra.addWidget(lbl_titulo)

    layout_barra.addStretch()

    # Botão Maximizar / Restaurar
    self.btn_maximizar = QPushButton('🗖')
    self.btn_maximizar.setFixedSize(26, 26)
    self.btn_maximizar.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 15);
                color: white;
                border-radius: 13px;
                font-size: 11px;
                border: none;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 40); }
        """)
    self.btn_maximizar.clicked.connect(self.toggle_maximizar)
    layout_barra.addWidget(self.btn_maximizar)

    # Botão Fechar
    btn_fechar = QPushButton('✕')
    btn_fechar.setFixedSize(26, 26)
    btn_fechar.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.8);
                color: white;
                border-radius: 13px;
                font-weight: bold;
                font-size: 11px;
                border: none;
            }
            QPushButton:hover { background-color: rgba(220, 38, 38, 1.0); }
        """)
    btn_fechar.clicked.connect(self.fechar_janela)
    layout_barra.addWidget(btn_fechar)

    layout_principal.addWidget(self.barra_titulo)

    # --- CORPO DA JANELA ---
    self.corpo = QFrame()
    self.corpo.setStyleSheet(
        'background: rgba(0, 0, 0, 70); border-radius: 8px; border: none;'
    )
    layout_corpo = QVBoxLayout(self.corpo)

    self.lbl_status = QLabel(
        f'🚀 App: {self.titulo_app}\n\nComando: {self.comando}'
    )
    self.lbl_status.setAlignment(Qt.AlignCenter)
    self.lbl_status.setStyleSheet(
        'color: #cbd5e1; font-size: 13px; background: transparent;'
    )
    layout_corpo.addWidget(self.lbl_status)

    layout_principal.addWidget(self.corpo)

  # --- LÓGICA DE ARRASTE FLUIDO ---
  def iniciar_arraste(self, event):
    if event.button() == Qt.LeftButton and not self.maximizada:
      self.arrastando = True
      self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
      self.raise_()
      event.accept()

  def mover_janela(self, event):
    if self.arrastando and (event.buttons() & Qt.LeftButton):
      nova_posicao = event.globalPos() - self.drag_position

      if self.parent():
        parent_rect = self.parent().rect()
        max_x = parent_rect.width() - self.width()
        max_y = parent_rect.height() - self.height() - 60

        x = max(0, min(nova_posicao.x(), max_x))
        y = max(0, min(nova_posicao.y(), max_y))
        self.move(x, y)
      else:
        self.move(nova_posicao)

      event.accept()

  def parar_arraste(self, event):
    self.arrastando = False

  def toggle_maximizar(self):
    """Alterna entre tela cheia e o tamanho normal."""
    if not self.maximizada:
      self.geometria_antiga = self.geometry()
      if self.parent():
        parent_rect = self.parent().rect()
        self.setGeometry(
            parent_rect.x() + 8,
            parent_rect.y() + 8,
            parent_rect.width() - 16,
            parent_rect.height() - 72,
        )
      self.btn_maximizar.setText('🗗')
      self.maximizada = True
    else:
      if self.geometria_antiga:
        self.setGeometry(self.geometria_antiga)
      self.btn_maximizar.setText('🗖')
      self.maximizada = False

  def executar_processo(self):
    try:
      args = shlex.split(self.comando)
      self.processo = subprocess.Popen(args)
    except Exception as e:
      self.lbl_status.setText(f'⚠️ Erro ao iniciar.\nDetalhe: {e}')

  def fechar_janela(self):
    if self.processo and self.processo.poll() is None:
      try:
        self.processo.terminate()
      except Exception:
        pass
    self.close()
    self.deleteLater()


class InterfaceDesktop(QWidget):

  def __init__(self):
    super().__init__()
    self.menu_aberto = False
    self.pixmap_wallpaper = None
    self.janela_energia = None
    self.initUI()

  def criar_wallpaper_padrao(self):
    pix = QPixmap(self.width(), self.height())
    painter = QPainter(pix)
    gradient = QLinearGradient(0, 0, self.width(), self.height())
    gradient.setColorAt(0.0, QColor(24, 28, 46))
    gradient.setColorAt(0.5, QColor(45, 30, 62))
    gradient.setColorAt(1.0, QColor(18, 18, 28))
    painter.setBrush(gradient)
    painter.drawRect(0, 0, self.width(), self.height())
    painter.end()
    return pix

  def paintEvent(self, event):
    painter = QPainter(self)
    if self.pixmap_wallpaper and not self.pixmap_wallpaper.isNull():
      scaled_pixmap = self.pixmap_wallpaper.scaled(
          self.size(),
          Qt.KeepAspectRatioByExpanding,
          Qt.SmoothTransformation,
      )
      painter.drawPixmap(0, 0, scaled_pixmap)
    else:
      painter.drawPixmap(0, 0, self.criar_wallpaper_padrao())

  def initUI(self):
    self.setWindowFlags(
        Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    )
    self.resize(800, 500)

    self.main_layout = QVBoxLayout(self)
    self.main_layout.setContentsMargins(15, 15, 15, 15)

    # --- LANÇADOR DE APLICATIVOS ---
    self.menu_iniciar = QFrame(self)
    self.menu_iniciar.setStyleSheet("""
            QFrame {
                background-color: rgba(20, 20, 30, 230);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 20px;
            }
        """)
    self.menu_layout = QVBoxLayout(self.menu_iniciar)

    cabecalho = QHBoxLayout()
    titulo_menu = QLabel('⚡ Boss_OS')
    titulo_menu.setFont(QFont('Ubuntu', 14, QFont.Weight.Bold))
    titulo_menu.setStyleSheet(
        'color: #ffffff; border: none; background: transparent;'
    )
    cabecalho.addWidget(titulo_menu)

    cabecalho.addStretch()

    self.btn_wallpaper = QPushButton('🖼️ Trocar Fundo')
    self.btn_wallpaper.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 25);
                color: white;
                border-radius: 12px;
                padding: 5px 10px;
                font-size: 11px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 60);
            }
        """)
    self.btn_wallpaper.clicked.connect(self.selecionar_wallpaper)
    cabecalho.addWidget(self.btn_wallpaper)

    self.menu_layout.addLayout(cabecalho)

    self.lista_apps = QListWidget()
    self.lista_apps.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: #ffffff; }
            QListWidget::item { padding: 8px; border-radius: 8px; }
            QListWidget::item:hover { background-color: rgba(255, 255, 255, 40); }
        """)
    self.lista_apps.setIconSize(QSize(24, 24))
    self.lista_apps.itemClicked.connect(self.abrir_aplicativo)
    self.menu_layout.addWidget(self.lista_apps)

    self.menu_iniciar.hide()
    self.main_layout.addWidget(self.menu_iniciar)

    self.main_layout.addStretch()

    # --- BARRA DE STATUS (DOCK) ---
    self.barra_status = QFrame(self)
    self.barra_status.setFixedHeight(55)
    self.barra_status.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 15, 25, 190);
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 25px;
            }
        """)

    layout_barra = QHBoxLayout(self.barra_status)
    layout_barra.setContentsMargins(15, 5, 15, 5)

    self.btn_iniciar = QPushButton(' Boss_OS')
    self.btn_iniciar.setIcon(QIcon.fromTheme('start-here'))
    self.btn_iniciar.setStyleSheet("""
            QPushButton {
                background-color: rgba(139, 92, 246, 0.4);
                color: white;
                border-radius: 15px;
                padding: 6px 15px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 40);
            }
            QPushButton:hover { background-color: rgba(139, 92, 246, 0.7); }
        """)
    self.btn_iniciar.clicked.connect(self.toggle_menu)
    layout_barra.addWidget(self.btn_iniciar)

    layout_barra.addStretch()

    # Relógio
    self.relogio = QLabel()
    self.relogio.setStyleSheet(
        'color: white; font-weight: bold; border: none; background:'
        ' transparent; font-size: 12px; padding-right: 10px;'
    )
    layout_barra.addWidget(self.relogio)

    self.timer_relogio = QTimer(self)
    self.timer_relogio.timeout.connect(self.atualizar_relogio)
    self.timer_relogio.start(1000)
    self.atualizar_relogio()

    # --- BOTÃO DE ENERGIA (POWER) ---
    self.btn_energia = QPushButton('⏻')
    self.btn_energia.setFixedSize(36, 36)
    self.btn_energia.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.3);
                color: #ef4444;
                border-radius: 18px;
                font-size: 16px;
                font-weight: bold;
                border: 1px solid rgba(239, 68, 68, 0.5);
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.8);
                color: white;
            }
        """)
    self.btn_energia.clicked.connect(self.abrir_menu_energia)
    layout_barra.addWidget(self.btn_energia)

    self.main_layout.addWidget(self.barra_status)

    self.carregar_apps()

  def toggle_menu(self):
    if self.menu_aberto:
      self.menu_iniciar.hide()
      self.menu_aberto = False
    else:
      self.menu_iniciar.show()
      self.menu_iniciar.raise_()
      self.menu_aberto = True

  def abrir_menu_energia(self):
    if self.janela_energia is None or not self.janela_energia.isVisible():
      self.janela_energia = JanelaEnergia(parent=self)
      self.janela_energia.show()
      self.janela_energia.raise_()

  def selecionar_wallpaper(self):
    caminho_imagem, _ = QFileDialog.getOpenFileName(
        self,
        'Escolher Papel de Parede',
        '',
        'Imagens (*.png *.jpg *.jpeg *.webp)',
    )
    if caminho_imagem:
      self.pixmap_wallpaper = QPixmap(caminho_imagem)
      self.update()

  def atualizar_relogio(self):
    agora = datetime.now()
    self.relogio.setText(agora.strftime('%d/%m/%Y | %H:%M:%S'))

  def carregar_apps(self):
    self.apps_dados = buscar_aplicativos()
    self.lista_apps.clear()

    if not self.apps_dados:
      item = QListWidgetItem(
          QIcon.fromTheme('utilities-terminal'), 'Termux Terminal'
      )
      item.setData(Qt.UserRole, 'termux')
      self.lista_apps.addItem(item)
    else:
      for app in self.apps_dados:
        item = QListWidgetItem(QIcon.fromTheme(app['icone']), app['nome'])
        item.setData(Qt.UserRole, app['exec'])
        self.lista_apps.addItem(item)

  def abrir_aplicativo(self, item):
    nome_app = item.text()
    comando = item.data(Qt.UserRole)

    self.toggle_menu()

    janela = JanelaApp(nome_app, comando, parent=self)
    janela.show()
    janela.raise_()


if __name__ == '__main__':
  app = QApplication(sys.argv)
  window = InterfaceDesktop()
  window.show()
  sys.exit(app.exec_())

