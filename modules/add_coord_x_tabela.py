"""
/***************************************************************************
 RMCGeo
                                 A QGIS plugin
 Conjunto de ferramentas para simplificar tarefas geoespaciais.
                             -------------------
        begin                : 2025-06-01
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

from .base_field_calculator import BaseCalculadoraTabela
from qgis.core import QgsWkbTypes
from qgis.PyQt.QtCore import QVariant


class CoordXTabelaDialog(BaseCalculadoraTabela):
    """Adiciona campo com coordenada X"""
    
    window_title = "Adicionar Coordenada X na Tabela"
    field_name = "Coord_X"
    field_type = QVariant.String
    expression_string = "to_string($x)"
    geometry_types = [QgsWkbTypes.PointGeometry]  # Apenas pontos


def run(iface):
    """Função principal que abre o diálogo"""
    dialog = CoordXTabelaDialog(iface)
    # Compatibilidade Qt5/Qt6: exec_() foi renomeado para exec()
    if hasattr(dialog, 'exec'):
        dialog.exec()
    else:
        dialog.exec_()
