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

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QCursor
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
from qgis.gui import QgsMapTool
import webbrowser


class street_view_class(QgsMapTool):
    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.setCursor(QCursor(Qt.CrossCursor))

    def canvasPressEvent(self, event):
        # Verifica se foi clique com botão direito
        if event.button() == Qt.RightButton:
            self.canvas.unsetMapTool(self)
            return
            
        point = self.toMapCoordinates(event.pos())
        source_crs = self.canvas.mapSettings().destinationCrs()
        dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
        transformed_point = transform.transform(point)

        longitude = transformed_point.x()
        latitude = transformed_point.y()

        street_view_url = f"https://www.google.com/maps/@{latitude},{longitude},3a,75y,90t/data=!3m6!1e1!3m4!1s!2e0!7i16384!8i8192"
        webbrowser.open(street_view_url)
        self.canvas.unsetMapTool(self)  # Desativa a ferramenta após o clique
        self.iface.messageBar().pushMessage("Street View", "Street View aberto!", level=3)


def street_view(iface):
    """Função para ativar a ferramenta Street View."""
    canvas = iface.mapCanvas()
    tool = street_view_class(canvas, iface)
    canvas.setMapTool(tool)
    iface.messageBar().pushMessage("Street View", "Clique no mapa para abrir o Street View", level=3)

def run(iface):
    street_view(iface)

def unload():
    pass