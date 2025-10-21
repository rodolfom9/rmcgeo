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


class ComprimentoTabelaDialog(BaseCalculadoraTabela):
    """Adiciona campo com comprimento da linha em metros"""
    
    window_title = "Adicionar Comprimento na Tabela"
    field_name = "Comp_m"  # Valor padrão inicial (será atualizado pelo formato)
    field_type = QVariant.String
    expression_string = "format_number($length, 3)"  # Padrão: metros
    geometry_types = [QgsWkbTypes.LineGeometry]  # Apenas linhas
    
    # Opções de formatação disponíveis
    format_options = {
        "Metros (m)": "format_number($length, 3)",
        "Quilômetros (km)": "format_number($length/1000, 3)",
        "Centímetros (cm)": "format_number($length*100, 2)"
    }
    
    # Mapeamento de nomes de campo por formato
    field_names_by_format = {
        "Metros (m)": "Comp_m",
        "Quilômetros (km)": "Comp_km",
        "Centímetros (cm)": "Comp_cm"
    }


def run(iface):
    """Função principal que abre o diálogo"""
    dialog = ComprimentoTabelaDialog(iface)
    # Compatibilidade Qt5/Qt6: exec_() foi renomeado para exec()
    if hasattr(dialog, 'exec'):
        dialog.exec()
    else:
        dialog.exec_()
