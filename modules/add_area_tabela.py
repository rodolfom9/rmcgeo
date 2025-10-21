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


class AreaTabelaDialog(BaseCalculadoraTabela):
    """Adiciona campo de área em hectares"""
    
    window_title = "Adicionar Área na Tabela de Atributos"
    field_name = "Area_ha"  # Valor padrão inicial (será atualizado pelo formato)
    field_type = QVariant.String
    expression_string = "format_number($area/10000,2)"  # Padrão: hectares
    geometry_types = [QgsWkbTypes.PolygonGeometry]  # Apenas polígonos
    
    # Opções de formatação disponíveis
    format_options = {
        "Hectares (ha)": "format_number($area/10000,2)",
        "Metros² (m²)": "format_number($area,2)",
        "Quilômetros² (km²)": "format_number($area/1000000,3)",
        "Acres": "format_number($area/4046.86,3)"
    }
    
    # Mapeamento de nomes de campo por formato
    field_names_by_format = {
        "Hectares (ha)": "Area_ha",
        "Metros² (m²)": "Area_m2",
        "Quilômetros² (km²)": "Area_km2",
        "Acres": "Area_acres"
    }


def run(iface):
    """Função principal que abre o diálogo"""
    dialog = AreaTabelaDialog(iface)
    # Compatibilidade Qt5/Qt6: exec_() foi renomeado para exec()
    if hasattr(dialog, 'exec'):
        dialog.exec()
    else:
        dialog.exec_()
