import configparser
from datetime import datetime
import os
import shlex
import shutil
import subprocess
import sys

from PyQt5.QtCore import QPoint, QSize, Qt, QTimer
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMdiArea,
    QMdiSubWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def buscar_aplicativos():
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
                background-color: rgba(20, 20, 32, 245);
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
            QPushButton:hover { background-color: rgba(255, 255, 255, 40); }
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


class JanelaAppInterna(QMdiSubWindow):

  def __init__(self, titulo, comando, parent=None):
    super().__init__(parent)
    self.titulo_app = titulo
    self.comando = comando
    self.processo = None

    self.setWindowTitle(titulo)
    self.resize(650, 420)

    self.widget_conteudo = QWidget()
    self.setWidget(self.widget_conteudo)

    self.widget_conteudo.setStyleSheet("""
            QWidget {
                background-color: #1a1b26;
                color: white;
                border-radius: 8px;
            }
        """)

    layout = QVBoxLayout(self.widget_conteudo)

    self.lbl_status = QLabel(
        f'🚀 Executando: {self.titulo_app}\n\nComando: {self.comando}'
    )
    self.lbl_status.setAlignment(Qt.AlignCenter)
    self.lbl_status.setStyleSheet(
        'color: #cbd5e1; font-size: 13px; background: transparent;'
    )
    layout.addWidget(self.lbl_status)

    self.executar_processo()

  def executar_processo(self):
    try:
      args = shlex.split(self.comando)
      self.processo = subprocess.Popen(args)
    except Exception as e:
      self.lbl_status.setText(f'⚠️ Erro ao iniciar programa.\nDetalhe: {e}')

  def closeEvent(self, event):
    if self.processo and self.processo.poll() is None:
      try:
        self.processo.terminate()
      except Exception:
        pass
    event.accept()


class InterfaceDesktop(QWidget):

  def __init__(self):
    super().__init__()
    self.menu_aberto = False
    self.pixmap_wallpaper = None
    self.janela_energia = None
    self.initUI()

  def paintEvent(self, event):
    painter = QPainter(self)

    if self.pixmap_wallpaper and not self.pixmap_wallpaper.isNull():
      scaled = self.pixmap_wallpaper.scaled(
          self.size(),
          Qt.KeepAspectRatioByExpanding,
          Qt.SmoothTransformation,
      )
      painter.drawPixmap(0, 0, scaled)
    else:
      # Gradiente moderno do Boss_OS
      gradient = QLinearGradient(0, 0, self.width(), self.height())
      gradient.setColorAt(0.0, QColor(24, 28, 46))
      gradient.setColorAt(0.5, QColor(45, 30, 62))
      gradient.setColorAt(1.0, QColor(18, 18, 28))
      painter.setBrush(gradient)
      painter.drawRect(0, 0, self.width(), self.height())

  def initUI(self):
    self.setWindowFlags(Qt.FramelessWindowHint)

    self.main_layout = QVBoxLayout(self)
    self.main_layout.setContentsMargins(0, 0, 0, 0)
    self.main_layout.setSpacing(0)

    # --- ÁREA DE TRABALHO MDI (TRANSPARÊNCIA CORRIGIDA) ---
    self.area_trabalho = QMdiArea()
    self.area_trabalho.setBackground(QBrush(QColor(0, 0, 0, 0)))
    self.area_trabalho.viewport().setStyleSheet('background: transparent;')
    self.area_trabalho.setStyleSheet(
        'QMdiArea { background: transparent; border: none; }'
    )
    self.main_layout.addWidget(self.area_trabalho)

    # --- MENU INICIAR ---
    self.menu_iniciar = QFrame(self)
    self.menu_iniciar.setFixedSize(320, 420)
    self.menu_iniciar.setStyleSheet("""
            QFrame {
                background-color: rgba(20, 20, 30, 245);
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

    self.btn_wallpaper = QPushButton('🖼️ Fundo')
    self.btn_wallpaper.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 25);
                color: white;
                border-radius: 12px;
                padding: 5px 10px;
                font-size: 11px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 60); }
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

    # --- BARRA DE TAREFAS / DOCK INFERIOR ---
    container_barra = QWidget(self)
    container_layout = QHBoxLayout(container_barra)
    container_layout.setContentsMargins(15, 0, 15, 12)

    self.barra_status = QFrame(container_barra)
    self.barra_status.setFixedHeight(58)
    self.barra_status.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 15, 25, 220);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 28px;
            }
        """)

    layout_barra = QHBoxLayout(self.barra_status)
    layout_barra.setContentsMargins(15, 5, 15, 5)

    self.btn_iniciar = QPushButton(' Boss_OS')
    self.btn_iniciar.setIcon(QIcon.fromTheme('start-here'))
    self.btn_iniciar.setStyleSheet("""
            QPushButton {
                background-color: rgba(139, 92, 246, 0.5);
                color: white;
                border-radius: 16px;
                padding: 6px 16px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 40);
            }
            QPushButton:hover { background-color: rgba(139, 92, 246, 0.8); }
        """)
    self.btn_iniciar.clicked.connect(self.toggle_menu)
    layout_barra.addWidget(self.btn_iniciar)

    layout_barra.addStretch()

    self.relogio = QLabel()
    self.relogio.setStyleSheet(
        'color: white; font-weight: bold; border: none; background:'
        ' transparent; font-size: 13px; padding-right: 10px;'
    )
    layout_barra.addWidget(self.relogio)

    self.timer_relogio = QTimer(self)
    self.timer_relogio.timeout.connect(self.atualizar_relogio)
    self.timer_relogio.start(1000)
    self.atualizar_relogio()

    self.btn_energia = QPushButton('⏻')
    self.btn_energia.setFixedSize(36, 36)
    self.btn_energia.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.4);
                color: #ef4444;
                border-radius: 18px;
                font-size: 16px;
                font-weight: bold;
                border: 1px solid rgba(239, 68, 68, 0.5);
            }
            QPushButton:hover { background-color: rgba(239, 68, 68, 0.9); color: white; }
        """)
    self.btn_energia.clicked.connect(self.abrir_menu_energia)
    layout_barra.addWidget(self.btn_energia)

    container_layout.addWidget(self.barra_status)
    self.main_layout.addWidget(container_barra)

    self.carregar_apps()

  def resizeEvent(self, event):
    super().resizeEvent(event)
    self.menu_iniciar.move(20, self.height() - 500)

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
          QIcon.fromTheme('utilities-terminal'), 'Xfce Terminal'
      )
      item.setData(Qt.UserRole, 'xfce4-terminal')
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

    janela = JanelaAppInterna(nome_app, comando, parent=self)
    self.area_trabalho.addSubWindow(janela)
    janela.show()


if __name__ == '__main__':
  app = QApplication(sys.argv)
  window = InterfaceDesktop()
  window.showMaximized()
  sys.exit(app.exec_())

