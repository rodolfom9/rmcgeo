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

from .rumo_azimute_base import BaseBearingTool
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QTableWidgetItem, QMessageBox, QHeaderView, QAbstractItemView
from qgis.core import Qgis
import os

# Carrega o arquivo .ui
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'ui', 'azimuth_distance.ui'))


class AzimuthDistanceTool(BaseBearingTool):
    """Ferramenta para desenhar linhas usando azimute e distância."""
    
    def get_nome_camada(self):
        """Retorna o nome da camada."""
        return "Linhas_Azimute"

    def setup_table(self):
        """Configura a tabela com 2 colunas para azimute e distância."""
        table = self.dlg.coordenadasTable
        header = table.horizontalHeader()
        # Compatibilidade Qt5/Qt6:
        try:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # Qt6
        except AttributeError:
            header.setSectionResizeMode(QHeaderView.Stretch)  # Qt5
        
        table.setColumnCount(2)
        
        # Compatibilidade Qt5/Qt6:
        try:
            # Qt6
            table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | 
                                 QAbstractItemView.EditTrigger.EditKeyPressed)
        except AttributeError:
            # Qt5
            table.setEditTriggers(QAbstractItemView.DoubleClicked | 
                             QAbstractItemView.EditKeyPressed)
        
        table.cellChanged.connect(self.ao_mudar_celula)

    def show_dialog(self):
        """Mostra o diálogo para entrada de azimute e distância."""
        if not self.dlg:
            self.dlg = AzimuthDistanceDialog(self.iface)
            # Configurar tabela
            self.setup_table()
            # Conectar botões
            self.dlg.inserirButton.clicked.connect(self.insert_values)
            self.dlg.desfazerButton.clicked.connect(self.undo_last_insert)
            self.dlg.salvarButton.clicked.connect(self.save_and_close)
            # Conectar eventos de mudança nos inputs para atualizar preview
            self.dlg.azimuteInput.textChanged.connect(self.atualizar_preview)
            self.dlg.distanciaInput.textChanged.connect(self.atualizar_preview)
        self.dlg.show()

    def format_azimuth(self, dms_str):
        """Formata o azimute com símbolos de graus, minutos e segundos."""
        try:
            parts = dms_str.strip().split()
            if len(parts) == 1:
                return f"{float(parts[0]):.0f}°"
            elif len(parts) == 2:
                return f"{float(parts[0]):.0f}° {float(parts[1]):.0f}'"
            elif len(parts) == 3:
                return f"{float(parts[0]):.0f}° {float(parts[1]):.0f}' {float(parts[2]):.2f}\""
            else:
                return dms_str
        except ValueError:
            return dms_str

    def insert_values(self):
        """Insere os valores atuais na tabela."""
        try:
            # Converter azimute de DMS para decimal
            azimuth_dms = self.dlg.azimuteInput.text()
            azimuth = self.dms_to_decimal(azimuth_dms)
            
            if azimuth is None or azimuth < 0 or azimuth > 360:
                self.iface.messageBar().pushMessage(
                    "Erro", 
                    "Azimute inválido. O valor deve estar entre 0 e 360 graus. Use: '55' (graus) ou '55 55' (graus minutos) ou '55 55 55' (graus minutos segundos)",
                    level=Qgis.Warning
                )
                return
                
            if not self.dlg.distanciaInput.text():
                self.iface.messageBar().pushMessage(
                    "Erro", 
                    "Por favor, insira um valor para a distância.",
                    level=Qgis.Warning
                )
                return
                
            distance = float(self.dlg.distanciaInput.text())
            
            if distance <= 0:
                self.iface.messageBar().pushMessage(
                    "Erro", 
                    "A distância deve ser maior que zero.",
                    level=Qgis.Warning
                )
                return
                
            self.inserted_values.append((azimuth, distance))
            
            # Desconectar o sinal para evitar recursão ao adicionar itens
            table = self.dlg.coordenadasTable
            table.cellChanged.disconnect(self.ao_mudar_celula)
            
            row = table.rowCount()
            table.insertRow(row)
            
            # Mostrar o valor formatado na tabela
            table.setItem(row, 0, QTableWidgetItem(self.format_azimuth(azimuth_dms)))
            table.setItem(row, 1, QTableWidgetItem(f"{distance:.2f}m"))
            
            # Reconectar o sinal após inserir os itens
            table.cellChanged.connect(self.ao_mudar_celula)
            
            self.dlg.azimuteInput.clear()
            self.dlg.distanciaInput.clear()
            
            self.atualizar_preview()
            
        except ValueError:
            self.iface.messageBar().pushMessage(
                "Erro", 
                "Por favor, insira valores válidos para azimute e distância",
                level=Qgis.Warning
            )

    def ao_mudar_celula(self, row, column):
        """Atualiza os valores quando a tabela é editada pelo usuário."""
        try:
            table = self.dlg.coordenadasTable
            
            if row >= len(self.inserted_values):
                return
                
            cell_text = table.item(row, column).text()
            
            if column == 0:
                # Remove símbolo de grau, minuto e segundo se existir
                clean_text = cell_text.replace('°', ' ').replace("'", ' ').replace('"', ' ')
                clean_text = ' '.join(clean_text.split())
                
                azimuth = self.dms_to_decimal(clean_text)
                if azimuth is None or azimuth < 0 or azimuth > 360:
                    self.iface.messageBar().pushMessage(
                        "Erro", 
                        "Azimute inválido. O valor deve estar entre 0 e 360 graus.",
                        level=Qgis.Warning
                    )
                    
                    table.cellChanged.disconnect(self.ao_mudar_celula)
                    old_azimuth = self.inserted_values[row][0]
                    table.setItem(row, column, QTableWidgetItem(f"{old_azimuth:.2f}°"))
                    table.cellChanged.connect(self.ao_mudar_celula)
                    return
                    
                original_distance = self.inserted_values[row][1]
                self.inserted_values[row] = (azimuth, original_distance)
                
            elif column == 1:  # Distância
                clean_text = cell_text.replace('m', '').strip()
                
                try:
                    distance = float(clean_text)
                    if distance <= 0:
                        raise ValueError("Distância deve ser maior que zero")
                        
                    original_azimuth = self.inserted_values[row][0]
                    self.inserted_values[row] = (original_azimuth, distance)
                    
                    table.cellChanged.disconnect(self.ao_mudar_celula)
                    table.setItem(row, column, QTableWidgetItem(f"{distance:.2f}m"))
                    table.cellChanged.connect(self.ao_mudar_celula)
                    
                except ValueError:
                    self.iface.messageBar().pushMessage(
                        "Erro", 
                        "Distância inválida. Use um valor numérico maior que zero.",
                        level=Qgis.Warning
                    )
                    
                    table.cellChanged.disconnect(self.ao_mudar_celula)
                    old_distance = self.inserted_values[row][1]
                    table.setItem(row, column, QTableWidgetItem(f"{old_distance:.2f}m"))
                    table.cellChanged.connect(self.ao_mudar_celula)
                    return
            
            self.atualizar_preview()
            
        except Exception as e:
            print(f"DEBUG: Erro ao atualizar valor na tabela: {str(e)}")
            self.atualizar_preview()

    def atualizar_preview(self):
        """Atualiza o preview com o estado atual."""
        try:
            azimuth_dms = self.dlg.azimuteInput.text()
            azimuth = self.dms_to_decimal(azimuth_dms)
            distance = float(self.dlg.distanciaInput.text()) if self.dlg.distanciaInput.text() else None
            self.preview_line(self.start_point, azimuth, distance)
        except ValueError:
            pass


class AzimuthDistanceDialog(QtWidgets.QDialog, FORM_CLASS):
    """Diálogo para entrada de azimute e distância."""
    
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setupUi(self)
        
        # Carregar o ícone SVG
        svg_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'icon.svg'
        )
        if os.path.exists(svg_path):
            icon = QIcon(svg_path)
            pixmap = icon.pixmap(QSize(32, 32))
            self.icon.setPixmap(pixmap)
            self.icon.setText("")
            
        # Conectar sinais para validação em tempo real
        self.azimuteInput.textChanged.connect(self.validar_azimute)
        self.distanciaInput.textChanged.connect(self.validar_distancia)
        
    def validar_azimute(self, text):
        """Validação em tempo real para entrada de azimute."""
        if not text:
            self.azimuteInput.setStyleSheet("")
            return
            
        try:
            parts = text.strip().split()
            valid = True
            
            if len(parts) == 1:
                graus = float(parts[0])
                valid = 0 <= graus <= 360
            elif len(parts) == 2:
                graus = float(parts[0])
                minutos = float(parts[1])
                valid = (0 <= graus <= 360) and (0 <= minutos < 60)
            elif len(parts) == 3:
                graus = float(parts[0])
                minutos = float(parts[1])
                segundos = float(parts[2])
                valid = (0 <= graus <= 360) and (0 <= minutos < 60) and (0 <= segundos < 60)
            else:
                valid = False
                
            if not valid:
                self.azimuteInput.setStyleSheet("background-color: #ffcccc;")
                if self.iface:
                    self.iface.statusBarIface().showMessage("Azimute deve estar entre 0 e 360 graus", 3000)
            else:
                self.azimuteInput.setStyleSheet("")
                
        except ValueError:
            self.azimuteInput.setStyleSheet("background-color: #ffcccc;")
    
    def validar_distancia(self, text):
        """Validação em tempo real para entrada de distância."""
        if not text:
            self.distanciaInput.setStyleSheet("")
            return
            
        try:
            distancia = float(text)
            if distancia <= 0:
                self.distanciaInput.setStyleSheet("background-color: #ffcccc;")
                if self.iface:
                    self.iface.statusBarIface().showMessage("Distância deve ser maior que zero", 3000)
            else:
                self.distanciaInput.setStyleSheet("")
        except ValueError:
            self.distanciaInput.setStyleSheet("background-color: #ffcccc;")


def run(iface):
    """Função para executar a ferramenta de azimute e distância."""
    canvas = iface.mapCanvas()
    crs = canvas.mapSettings().destinationCrs()
    
    # Verificar se é sistema de coordenadas projetado e se é UTM
    if crs.isGeographic():
        QMessageBox.warning(
            iface.mainWindow(),
            "Sistema de Coordenadas Inválido",
            "Esta ferramenta funciona apenas com sistemas de coordenadas UTM.\n\n"
            "Por favor, altere o sistema de coordenadas do projeto para UTM."
        )
        return
    
    # Verificar se a projeção contém "UTM" ou "Transverse Mercator" no nome
    proj_name = crs.description().upper()
    projection_method = crs.projectionAcronym().upper()
    
    is_utm = ("UTM" in proj_name or 
              "UTM" in projection_method or 
              "UNIVERSAL TRANSVERSE MERCATOR" in proj_name)
    
    if not is_utm:
        QMessageBox.warning(
            iface.mainWindow(),
            "Sistema de Coordenadas Inválido",
            f"Esta ferramenta funciona apenas com sistemas de coordenadas UTM.\n\n"
            f"Sistema atual: {crs.description()}\n\n"
            f"Por favor, altere o sistema de coordenadas do projeto para UTM."
        )
        return
    
    tool = AzimuthDistanceTool(canvas, iface)
    canvas.setMapTool(tool)
    iface.messageBar().pushMessage(
        "Instrução",
        "Clique no mapa para definir o ponto inicial da linha.",
        level=Qgis.Info,
        duration=5
    )