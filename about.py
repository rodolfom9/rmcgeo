"""
/***************************************************************************
 RMCGeo
                                 A QGIS plugin
 Conjunto de ferramentas para simplificar tarefas geoespaciais.
                             -------------------
        begin                : 2025-01-10
        copyright            : (C) 2025 by Rodolfo Martins de Carvalho
        email                : rodolfomartins09@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtGui import QPixmap, QIcon
from qgis.PyQt.QtCore import QSize

import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'about.ui'))

class AboutDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        # Aqui você pode preencher campos dinamicamente, se quiser
        self.plugin_name.setText("RMCGEO")
        self.plugin_version.setText("Versão 1.7.0")
        
        # Conecta o botão de fechar
        self.close.accepted.connect(self.accept)
        self.close.rejected.connect(self.reject)
        
        # Carrega o ícone SVG no QLabel
        self.carregar_icon()
        
        # Carrega o arquivo de informações
        info_path = os.path.join(os.path.dirname(__file__), 'utils', 'info.html')
        try:
            with open(info_path, 'r', encoding='utf-8') as f:
                info_text = f.read()
            self.information.setHtml(info_text)
        except Exception as e:
            self.information.setPlainText("Erro ao carregar arquivo de informação.")

        # Carrega o arquivo da licença
        license_path = os.path.join(os.path.dirname(__file__), 'utils', 'GNU General Public License v3.0.html')
        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                license_text = f.read()
            self.license.setHtml(license_text)
        except Exception as e:
            self.license.setPlainText("Erro ao carregar arquivo da licença.")
    
    def carregar_icon(self):
        """Carrega o ícone SVG no QLabel"""
        try:
            # Caminho para o ícone SVG
            svg_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
            
            # Verifica se o arquivo existe
            if os.path.exists(svg_path):
                # Cria um QIcon a partir do arquivo SVG
                icon = QIcon(svg_path)
                # Converte o QIcon para QPixmap com o tamanho desejado
                pixmap = icon.pixmap(QSize(64, 64))
                # Define o pixmap no QLabel
                self.plugin_icon.setPixmap(pixmap)
            else:
                # Caso o arquivo não exista, tenta usar um ícone padrão do QGIS
                self.plugin_icon.setPixmap(QIcon(':/images/themes/default/mActionShowPluginManager.svg').pixmap(QSize(64, 64)))
        except Exception as e:
            print(f"Erro ao carregar ícone: {e}")