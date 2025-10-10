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


class AzimuteTabelaDialog(BaseCalculadoraTabela):
    """Adiciona campo de azimute em formato GMS ou Decimal"""
    
    window_title = "Adicionar Azimute em GMS na Tabela"
    field_name = "Azimute_GMS"  # Valor padrão inicial (será atualizado pelo formato)
    field_type = QVariant.String
    geometry_types = [QgsWkbTypes.LineGeometry]  # Apenas linhas
    
    # Opções de formatação disponíveis
    format_options = {
        "GMS (Graus° Minutos' Segundos\")": """
            with_variable('azim', degrees(azimuth(start_point($geometry), end_point($geometry))),
                with_variable('graus', floor(@azim),
                    with_variable('minutos', floor((@azim - @graus) * 60),
                        with_variable('segundos', ((@azim - @graus) * 60 - @minutos) * 60,
                            @graus || '° ' || @minutos || ''' ' || round(@segundos, 2) || '"'
                        )
                    )
                )
            )
        """,
        "Decimal (Graus)": "format_number(degrees(azimuth(start_point($geometry), end_point($geometry))), 4)"
    }
    
    # Mapeamento de nomes de campo por formato
    field_names_by_format = {
        "GMS (Graus° Minutos' Segundos\")": "Azimute_GMS",
        "Decimal (Graus)": "Azimute_Dec"
    }


def run(iface):
    """Função principal que abre o diálogo"""
    dialog = AzimuteTabelaDialog(iface)
    dialog.exec_()
