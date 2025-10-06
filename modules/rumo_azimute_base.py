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

from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QHeaderView, QAbstractItemView
from qgis.core import (QgsPointXY, QgsProject, Qgis,
                      QgsGeometry, QgsVectorLayer, QgsFeature, QgsWkbTypes)
import math


class BaseBearingTool(QgsMapTool):
    """Classe base para ferramentas de azimute e rumo."""
    
    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.start_point = None
        self.rubber_band = None
        self.dlg = None
        self.setCursor(Qt.CrossCursor)
        
        self.inserted_values = [] # Lista para armazenar os valores inseridos
        
        # Criar rubber band para preview
        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.rubber_band.setColor(QColor(255, 0, 0))
        self.rubber_band.setWidth(2)

    def create_memory_layer(self, layer_name="Linhas"):
        """Cria uma camada temporária em UTM SIRGAS 2000 / UTM zone 22S."""
        layer = QgsVectorLayer(f"LineString?crs=EPSG:31982", layer_name, "memory")
        
        if not layer.isValid():
            self.iface.messageBar().pushMessage(
                "Erro", "Não foi possível criar a camada em UTM", level=Qgis.Critical)
            return None
            
        QgsProject.instance().addMapLayer(layer)
        return layer

    def dms_to_decimal(self, dms_str):
        """Converte graus, minutos e segundos para graus decimais."""
        try:
            parts = dms_str.strip().split()
            if len(parts) == 1:
                # Apenas graus
                decimal = float(parts[0])
            elif len(parts) == 2:
                # Graus e minutos
                degrees = float(parts[0])
                minutes = float(parts[1])
                decimal = degrees + (minutes / 60.0)
            elif len(parts) == 3:
                # Graus, minutos e segundos com decimais (limitado a 2 casas)
                degrees = float(parts[0])
                minutes = float(parts[1])
                # Limitar segundos a 2 casas decimais
                seconds = float(f"{float(parts[2]):.2f}")
                decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            else:
                return None
                
            return decimal
            
        except ValueError:
            return None

    def calculate_end_point(self, start_point, azimuth, distance):
        """Calcula o ponto final baseado no azimute e distância em UTM."""
        try:
            # Converter azimute para radianos e ajustar para o norte
            azimuth_rad = math.radians(90 - azimuth)
            
            # Calcular as coordenadas do ponto final em UTM
            dx = distance * math.cos(azimuth_rad)
            dy = distance * math.sin(azimuth_rad)
            
            # Criar ponto final em UTM
            end_point = QgsPointXY(
                start_point.x() + dx,
                start_point.y() + dy
            )
            
            return end_point
            
        except Exception as e:
            print(f"DEBUG: ERRO ao calcular ponto final: {str(e)}")
            return start_point

    def preview_line(self, start_point, azimuth, distance):
        """Mostra preview da linha usando rubber band."""
        if not self.rubber_band:
            return
            
        self.rubber_band.reset()
        current_point = start_point
        points = [current_point]
        
        # Desenhar linhas já inseridas
        for value_tuple in self.inserted_values:
            # Extrai azimute e distância (independente do tamanho da tupla)
            az = value_tuple[-2]  # Penúltimo elemento (azimute)
            dist = value_tuple[-1]  # Último elemento (distância)
            end_point = self.calculate_end_point(current_point, az, dist)
            points.append(end_point)
            current_point = end_point
        
        # Desenhar linha atual
        if azimuth is not None and distance is not None:
            end_point = self.calculate_end_point(current_point, azimuth, distance)
            points.append(end_point)
        
        if len(points) > 1:
            self.rubber_band.setToGeometry(
                QgsGeometry.fromPolylineXY(points), None)

    def setup_table(self):
        """Configura a tabela de coordenadas."""
        table = self.dlg.coordenadasTable
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        table.setColumnCount(2)
        
        # Permitir edição na tabela
        table.setEditTriggers(QAbstractItemView.DoubleClicked | 
                             QAbstractItemView.EditKeyPressed)
        
        table.cellChanged.connect(self.ao_mudar_celula)

    def undo_last_insert(self):
        """Remove o último valor inserido."""
        if self.inserted_values:
            self.inserted_values.pop()
            table = self.dlg.coordenadasTable
            
            # Desconectar o sinal para evitar problemas ao remover linha
            table.cellChanged.disconnect(self.ao_mudar_celula)
            
            table.removeRow(table.rowCount() - 1)
            
            # Reconectar o sinal após remover a linha
            table.cellChanged.connect(self.ao_mudar_celula)
            
            self.atualizar_preview()

    def save_and_close(self):
        """Adiciona as linhas na camada UTM mantendo em modo de edição."""
        if not self.start_point or not self.inserted_values:
            if self.dlg:
                self.dlg.close()
            self.canvas.unsetMapTool(self)
            return

        # Tentar usar a camada selecionada ou criar uma nova em UTM
        layer = self.canvas.currentLayer()
        if layer:
            # Verificar se a camada é UTM
            if layer.crs().authid() != 'EPSG:31982':
                self.iface.messageBar().pushMessage(
                    "Aviso", 
                    "A camada selecionada não está em UTM. Criando nova camada UTM.",
                    level=Qgis.Warning
                )
                layer = self.create_memory_layer(self.get_nome_camada())
            elif layer.geometryType() != QgsWkbTypes.LineGeometry:
                self.iface.messageBar().pushMessage(
                    "Aviso", 
                    "A camada selecionada não é do tipo linha. Criando nova camada.",
                    level=Qgis.Warning
                )
                layer = self.create_memory_layer(self.get_nome_camada())
        else:
            layer = self.create_memory_layer(self.get_nome_camada())

        if not layer or not layer.isValid():
            return

        # Garantir que a camada está em modo de edição
        if not layer.isEditable():
            if not layer.startEditing():
                return

        current_point = self.start_point
        total_lines = len(self.inserted_values)

        # Adicionar cada feature individualmente
        features_added = 0
        for i, value_tuple in enumerate(self.inserted_values):
            try:
                # Extrai azimute e distância (independente do tamanho da tupla)
                azimuth = value_tuple[-2]
                distance = value_tuple[-1]
                
                end_point = self.calculate_end_point(current_point, azimuth, distance)
                
                # Criar a geometria da linha
                line = QgsGeometry.fromPolylineXY([current_point, end_point])
                if not line.isGeosValid():
                    continue
                
                # Criar e adicionar a feature
                feat = QgsFeature(layer.fields())
                feat.setGeometry(line)
                
                # Tentar adicionar a feature
                if layer.addFeature(feat):
                    features_added += 1
                
                current_point = end_point
                
            except Exception as e:
                print(f"DEBUG: ERRO ao processar linha {i+1}: {str(e)}")
                continue

        if features_added > 0:
            # Atualizar a extensão da camada
            layer.updateExtents()
            
            self.iface.messageBar().pushMessage(
                "Sucesso",
                f"Foram adicionadas {features_added} linhas em UTM! A camada permanece em modo de edição.",
                level=Qgis.Success,
                duration=3
            )
        else:
            self.iface.messageBar().pushMessage(
                "Erro",
                "Não foi possível adicionar as linhas!",
                level=Qgis.Critical,
                duration=3
            )

        # Limpar e fechar
        if self.rubber_band:
            self.rubber_band.reset()
        if self.dlg:
            self.dlg.close()
        self.canvas.unsetMapTool(self)

    def canvasPressEvent(self, event):
        """Captura o clique no mapa."""
        # Verificar se há uma camada selecionada e se está em modo de edição
        layer = self.canvas.currentLayer()
        if layer and not layer.isEditable():
            self.iface.messageBar().pushMessage(
                "Aviso", 
                "A camada precisa estar em modo de edição para usar a ferramenta.",
                level=Qgis.Warning
            )
            return
            
        if not self.dlg or not self.dlg.isVisible():
            # Primeiro clique - pegar ponto inicial e mostrar diálogo
            self.start_point = self.toMapCoordinates(event.pos())
            self.show_dialog()
        else:
            # Cliques subsequentes - atualizar ponto inicial
            self.start_point = self.toMapCoordinates(event.pos())
            self.atualizar_preview()

    def canvasReleaseEvent(self, event):
        """Captura quando o botão do mouse é solto."""
        if event.button() == Qt.RightButton:
            # Fechar o diálogo se estiver aberto
            if self.dlg and self.dlg.isVisible():
                self.dlg.close()
            # Limpar o rubber band
            if self.rubber_band:
                self.rubber_band.reset()
            self.canvas.unsetMapTool(self) # Desativar a ferramenta

    def deactivate(self):
        """Limpa recursos ao desativar a ferramenta."""
        if self.rubber_band:
            self.rubber_band.reset()
        if self.dlg:
            self.dlg.close()
        super().deactivate()

