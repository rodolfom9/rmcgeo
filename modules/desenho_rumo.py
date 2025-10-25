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
from qgis.PyQt.QtWidgets import QTableWidgetItem, QMessageBox
from qgis.core import Qgis
import os

# Carrega o arquivo .ui
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'ui', 'rumo_distance.ui'))


class RumoDistanceTool(BaseBearingTool):
    """Ferramenta para desenhar linhas usando rumo (quadrante) e distância."""
    
    def get_nome_camada(self):
        """Retorna o nome da camada."""
        return "Linhas_Rumo"

    def show_dialog(self):
        """Mostra o diálogo para entrada de rumo e distância."""
        if not self.dlg:
            self.dlg = RumoDistanceDialog(self.iface)
            # Configurar tabela
            self.setup_table()
            # Conectar botões
            self.dlg.inserirButton.clicked.connect(self.insert_values)
            self.dlg.desfazerButton.clicked.connect(self.undo_last_insert)
            self.dlg.salvarButton.clicked.connect(self.save_and_close)
            self.dlg.rumoInput.textChanged.connect(self.atualizar_preview)
            self.dlg.quadranteCombo.currentTextChanged.connect(self.atualizar_preview)
            self.dlg.distanciaInput.textChanged.connect(self.atualizar_preview)
        self.dlg.show()

    def converter_rumo_azimute(self, rumo_decimal, quadrante):
        """Converte rumo decimal e quadrante para azimute"""
        try:
            if rumo_decimal < 0 or rumo_decimal > 90:
                return None
            
            # Converter para azimute baseado no quadrante
            if quadrante == 'NE':
                azimuth = rumo_decimal
            elif quadrante == 'SE':
                azimuth = 180 - rumo_decimal
            elif quadrante == 'SW':
                azimuth = 180 + rumo_decimal
            elif quadrante == 'NW':
                azimuth = 360 - rumo_decimal
            else:
                return None
            
            return azimuth
            
        except (ValueError, AttributeError):
            return None

    def format_rumo_dms(self, dms_str):
        """Formata o rumo com símbolos de graus, minutos e segundos."""
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
            # Converter rumo de DMS para decimal
            rumo_dms = self.dlg.rumoInput.text()
            quadrante = self.dlg.quadranteCombo.currentText()
            
            rumo_decimal = self.dms_to_decimal(rumo_dms)
            
            if rumo_decimal is None or rumo_decimal < 0 or rumo_decimal > 90:
                self.iface.messageBar().pushMessage(
                    "Erro", 
                    "Rumo inválido. O valor deve estar entre 0 e 90 graus. Use: '45' (graus) ou '45 30' (graus minutos) ou '45 30 15' (graus minutos segundos)",
                    level=Qgis.Warning
                )
                return
            
            azimuth = self.converter_rumo_azimute(rumo_decimal, quadrante)
            
            if azimuth is None:
                self.iface.messageBar().pushMessage(
                    "Erro", 
                    "Erro ao converter rumo para azimute.",
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
                
            # Criar string formatada do rumo para exibição
            rumo_formatted = f"{self.format_rumo_dms(rumo_dms)} {quadrante}"
            self.inserted_values.append((rumo_formatted, azimuth, distance))
            
            # Desconectar o sinal para evitar recursão ao adicionar itens
            table = self.dlg.coordenadasTable
            table.cellChanged.disconnect(self.ao_mudar_celula)
            
            row = table.rowCount()
            table.insertRow(row)
            
            # Mostrar o valor formatado na tabela
            table.setItem(row, 0, QTableWidgetItem(rumo_formatted))
            table.setItem(row, 1, QTableWidgetItem(f"{distance:.2f}m"))
            
            # Reconectar o sinal após inserir os itens
            table.cellChanged.connect(self.ao_mudar_celula)
            
            self.dlg.rumoInput.clear()
            self.dlg.distanciaInput.clear()
            
            self.atualizar_preview()
            
        except ValueError:
            self.iface.messageBar().pushMessage(
                "Erro", 
                "Por favor, insira valores válidos para rumo e distância",
                level=Qgis.Warning
            )

    def ao_mudar_celula(self, row, column):
        """Atualiza os valores quando a tabela é editada pelo usuário."""
        try:
            table = self.dlg.coordenadasTable
            
            if row >= len(self.inserted_values):
                return
                
            cell_text = table.item(row, column).text()
            
            if column == 0:  # Rumo
                # Para simplificar, vamos apenas restaurar o valor original
                # A edição de rumo é complexa porque envolve o quadrante
                self.iface.messageBar().pushMessage(
                    "Aviso", 
                    "Para editar o rumo, remova esta linha e insira novamente com os valores corretos.",
                    level=Qgis.Warning
                )
                
                table.cellChanged.disconnect(self.ao_mudar_celula)
                old_rumo = self.inserted_values[row][0]
                table.setItem(row, column, QTableWidgetItem(old_rumo))
                table.cellChanged.connect(self.ao_mudar_celula)
                return
                
            elif column == 1:  # Distância
                clean_text = cell_text.replace('m', '').strip()
                
                try:
                    distance = float(clean_text)
                    if distance <= 0:
                        raise ValueError("Distância deve ser maior que zero")
                        
                    original_rumo = self.inserted_values[row][0]
                    original_azimuth = self.inserted_values[row][1]
                    self.inserted_values[row] = (original_rumo, original_azimuth, distance)
                    
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
                    old_distance = self.inserted_values[row][2]
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
            rumo_dms = self.dlg.rumoInput.text()
            quadrante = self.dlg.quadranteCombo.currentText()
            
            rumo_decimal = self.dms_to_decimal(rumo_dms)
            azimuth = self.converter_rumo_azimute(rumo_decimal, quadrante) if rumo_decimal is not None else None
            
            distance = float(self.dlg.distanciaInput.text()) if self.dlg.distanciaInput.text() else None
            self.preview_line(self.start_point, azimuth, distance)
        except ValueError:
            pass


class RumoDistanceDialog(QtWidgets.QDialog, FORM_CLASS):
    """Diálogo para entrada de rumo e distância."""
    
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
        self.rumoInput.textChanged.connect(self.validar_rumo)
        self.quadranteCombo.currentTextChanged.connect(lambda: self.validar_rumo(self.rumoInput.text()))
        self.distanciaInput.textChanged.connect(self.validar_distancia)
        
    def validar_rumo(self, text):
        """Validação em tempo real para entrada de rumo."""
        if not text:
            self.rumoInput.setStyleSheet("")
            return
            
        try:
            parts = text.strip().split()
            valid = False
            
            if len(parts) == 1:
                graus = float(parts[0])
                valid = 0 <= graus <= 90
            elif len(parts) == 2:
                graus = float(parts[0])
                minutos = float(parts[1])
                valid = (0 <= graus <= 90) and (0 <= minutos < 60)
            elif len(parts) == 3:
                graus = float(parts[0])
                minutos = float(parts[1])
                segundos = float(parts[2])
                valid = (0 <= graus <= 90) and (0 <= minutos < 60) and (0 <= segundos < 60)
            else:
                valid = False
                
            if not valid:
                self.rumoInput.setStyleSheet("background-color: #ffcccc;")
                if self.iface:
                    self.iface.statusBarIface().showMessage("Rumo deve estar entre 0 e 90 graus", 3000)
            else:
                self.rumoInput.setStyleSheet("")
                
        except ValueError:
            self.rumoInput.setStyleSheet("background-color: #ffcccc;")
    
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
    """Função para executar a ferramenta de rumo e distância."""
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
    
    tool = RumoDistanceTool(canvas, iface)
    canvas.setMapTool(tool)
    iface.messageBar().pushMessage(
        "Instrução",
        "Clique no mapa para definir o ponto inicial da linha.",
        level=Qgis.Info,
        duration=5
    )
