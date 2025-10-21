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
from qgis.core import Qgis, QgsProject, QgsPointXY, QgsGeometry, QgsWkbTypes
from qgis.PyQt.QtGui import QCursor, QColor
from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtCore import Qt

class copy_coordenada(QgsMapTool):
    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        # Compatibilidade Qt5/Qt6: CursorShape enum
        try:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))  # Qt6
        except AttributeError:
            self.setCursor(QCursor(Qt.CrossCursor))  # Qt5
            
        # Configuração de snapping
        self.snap_utils = iface.mapCanvas().snappingUtils()

        # RubberBand apenas para o contorno colorido
        self.rubber_band_outline = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band_outline.setColor(QColor(255, 0, 255))  # Contorno magenta
        self.rubber_band_outline.setFillColor(QColor(0, 0, 0, 0))  # Preenchimento transparente
        self.rubber_band_outline.setWidth(3)  # Largura do contorno

    def canvasMoveEvent(self, event):
        """Atualiza o indicador visual de snapping enquanto o mouse se move."""
        screen_pos = event.pos()
        snap_match = self.snap_utils.snapToMap(screen_pos)

        # Limpa o indicador anterior
        self.rubber_band_outline.reset(QgsWkbTypes.PolygonGeometry)

        # Se houver um ponto aderido, exibe apenas o contorno colorido
        if snap_match.isValid() and snap_match.hasVertex():
            point = snap_match.point()

            pixel_size = 6  # Tamanho do raio em pixels (ajustável)
            map_units_per_pixel = self.canvas.mapUnitsPerPixel()  # Resolução atual do canvas
            buffer_size = pixel_size * map_units_per_pixel  # Converte pixels para unidades do mapa

            # Cria um círculo ao redor do ponto com tamanho fixo em pixels
            circle = QgsGeometry.fromPointXY(point).buffer(buffer_size, 16)  # 16 segmentos para um círculo suave
            self.rubber_band_outline.setToGeometry(circle, None)
            self.rubber_band_outline.show()

    def canvasPressEvent(self, event):
        """Captura o clique no mapa e copia as coordenadas no CRS atual para o clipboard."""
        # Verifica se foi clique com botão direito
        # Compatibilidade Qt5/Qt6: MouseButton enum
        try:
            right_button = Qt.MouseButton.RightButton  # Qt6
        except AttributeError:
            right_button = Qt.RightButton  # Qt5
        
        if event.button() == right_button:
            self.canvas.unsetMapTool(self)
            return
                    
        screen_pos = event.pos()
        # Usa o snapping com as configurações atuais do projeto
        snap_match = self.snap_utils.snapToMap(screen_pos)
        # Se houver um ponto aderido, usa as coordenadas dele
        if snap_match.isValid() and snap_match.hasVertex():
            point = snap_match.point()  # Ponto aderido no CRS do mapa
        else:
            point = self.toMapCoordinates(screen_pos)

        x, y = point.x(), point.y()

        # Obtém o sistema de coordenadas atual do mapa
        map_crs = self.canvas.mapSettings().destinationCrs()
        crs_name = map_crs.authid()

        # Formata as coordenadas como string (X, Y)
        coord_str = f"{x:.4f}, {y:.4f}"

        # Copia para o clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(coord_str)

        snap_status = " (com aderência)" if snap_match.isValid() and snap_match.hasVertex() else " (sem aderência)"

        # Mostra mensagem de sucesso com o CRS atual
        self.iface.messageBar().pushMessage(
            "Sucesso",
            f"Coordenadas {coord_str} (CRS: {crs_name}) copiadas para o clipboard{snap_status}!",
            level=Qgis.Info,
            duration=3
        )

        # Limpa o rubber band após o clique
        self.rubber_band_outline.reset(QgsWkbTypes.PolygonGeometry)

    def deactivate(self):
        self.rubber_band_outline.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()

def copy_coordenada_def(iface):
    canvas = iface.mapCanvas()
    tool = copy_coordenada(canvas, iface)
    canvas.setMapTool(tool)
    iface.messageBar().pushMessage(
        "Instrução",
        "Clique no mapa para copiar as coordenadas no CRS atual. Certifique-se de que o snapping está configurado!",
        level=Qgis.Info,
        duration=5
    )

def run(iface):
    copy_coordenada_def(iface)
    
def unload():
    pass
