"""
/***************************************************************************
 RMCGeo
                                 A QGIS plugin
 Conjunto de ferramentas para simplificar tarefas geoespaciais.
                             -------------------
        begin                : 2025-12-29
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

import os
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.core import QgsProject, QgsWkbTypes, QgsGeometry, QgsDistanceArea, QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox

# Carrega o arquivo .ui
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'ui', 'project_norms.ui'))

class ProjectNormsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        super(ProjectNormsDialog, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        
        # Filtro para mostrar apenas camadas de polígono nos combos
        self.comboBaseLayer.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.comboVerde.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.comboInst.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.comboViario.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.comboAPP.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.comboReserva.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.comboLotes.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        
        # Permitir seleção de 'Nenhuma Camada' nos itens de norma
        self.comboVerde.setAllowEmptyLayer(True)
        self.comboInst.setAllowEmptyLayer(True)
        self.comboViario.setAllowEmptyLayer(True)
        self.comboAPP.setAllowEmptyLayer(True)
        self.comboReserva.setAllowEmptyLayer(True)
        self.comboLotes.setAllowEmptyLayer(True)

        self.btnCalculate.clicked.connect(self.calculate)
        self.btnClose.clicked.connect(self.close)

    def tr(self, message):
        return QCoreApplication.translate('RMCGeo', message)

    def get_layer_area(self, layer):
        """Calcula a área total somada de todas as feições de uma camada."""
        if not layer:
            return 0.0
        
        total_area = 0.0
        
        # Usar QgsDistanceArea para cálculos precisos (respeitando elipsoide)
        da = QgsDistanceArea()
        da.setSourceCrs(layer.crs(), QgsProject.instance().transformContext())
        da.setEllipsoid(QgsProject.instance().ellipsoid())
        
        for feature in layer.getFeatures():
            if feature.hasGeometry():
                geom = feature.geometry()
                # Calcula área no plano ou elipsoide dependendo da config do projeto
                area = da.measureArea(geom)
                total_area += area
        
        return total_area

    def calculate(self):
        base_layer = self.comboBaseLayer.currentLayer()
        app_layer = self.comboAPP.currentLayer() # APP
        reserva_layer = self.comboReserva.currentLayer() # Reserva Legal

        if not base_layer:
            self.iface.messageBar().pushMessage(
                "Erro", 
                "Selecione uma camada base (Gleba Total) primeiro.",
                level=3
            )
            return

        total_gleba_area = self.get_layer_area(base_layer)
        app_area = self.get_layer_area(app_layer)
        reserva_area = self.get_layer_area(reserva_layer)
        
        # A área parcelável exclui APP e Reserva Legal
        restricao_total = app_area + reserva_area
        parcelable_area = total_gleba_area - restricao_total

        if parcelable_area <= 0:
            self.iface.messageBar().pushMessage(
                "Erro", 
                "A área parcelável resultante é zero ou negativa (verifique APP/Reserva).",
                level=3
            )
            return

        summary_text = f"<b>Resumo da Análise (Goiânia - LC 349/2022)</b><br>"
        summary_text += f"Área Total da Gleba: {total_gleba_area:,.2f} m²<br>"
        summary_text += f"Área de APP: {app_area:,.2f} m²<br>"
        summary_text += f"Área de Reserva Legal: {reserva_area:,.2f} m²<br>"
        summary_text += f"<b>Área Parcelável (Base de Cálculo): {parcelable_area:,.2f} m²</b><br><br>"
        
        summary_text += "<table border='1' width='100%'>"
        summary_text += f"<tr><th>Categoria</th><th>Área (m²)</th><th>% s/ Parcelável</th></tr>"

        # Categorias para a tabela
        categories = [
            ("Áreas Verdes (Pq. Urbano)", self.comboVerde.currentLayer(), self.lblResultVerde),
            ("Ár. Institucionais (Equip.)", self.comboInst.currentLayer(), self.lblResultInst),
            ("Sistema Viário", self.comboViario.currentLayer(), self.lblResultViario),
            ("APP", self.comboAPP.currentLayer(), self.lblResultAPP),
            ("Reserva Legal", self.comboReserva.currentLayer(), self.lblResultReserva),
            ("Lotes/Quadras", self.comboLotes.currentLayer(), self.lblResultLotes),
        ]

        verde_area = self.get_layer_area(self.comboVerde.currentLayer())
        inst_area = self.get_layer_area(self.comboInst.currentLayer())
        viario_area = self.get_layer_area(self.comboViario.currentLayer())
        lotes_area = self.get_layer_area(self.comboLotes.currentLayer())

        for name, layer, result_label in categories:
            area = self.get_layer_area(layer)
            # Para a tabela, vamos mostrar a % em relação à GLEBA TOTAL para ficar claro
            percentage = (area / total_gleba_area) * 100
            result_label.setText(f"{percentage:.2f}%")
            summary_text += f"<tr><td>{name}</td><td>{area:,.2f}</td><td>{percentage:.2f}%</td></tr>"

        summary_text += "</table>"
        
        # Avaliação baseada no Art. 126 (Lei de Goiânia)
        # APMs (Verde e Inst) são calculados sobre a ÁREA PARCELÁVEL
        pct_verde_s_parcelavel = (verde_area / parcelable_area) * 100
        pct_inst_s_parcelavel = (inst_area / parcelable_area) * 100
        pct_total_apm_s_parcelavel = pct_verde_s_parcelavel + pct_inst_s_parcelavel
        
        # Ocupação total: soma de TUDO em relação à GLEBA TOTAL
        area_ocupada_total = verde_area + inst_area + viario_area + app_area + reserva_area + lotes_area
        pct_ocupacao_global = (area_ocupada_total / total_gleba_area) * 100
        
        summary_text += f"<br><b>Avaliação Técnica (Art. 126)</b>:<br>"
        
        # Validação Área Verde (7.5% da Parcelável)
        status_verde = "✅ OK" if pct_verde_s_parcelavel >= 7.5 else "❌ ABAIXO"
        summary_text += f"• Áreas Verdes: {pct_verde_s_parcelavel:.2f}% (Mín. 7.5% da área parc.) - {status_verde}<br>"
        
        # Validação Institucional (7.5% da Parcelável)
        status_inst = "✅ OK" if pct_inst_s_parcelavel >= 7.5 else "❌ ABAIXO"
        summary_text += f"• Áreas Institucionais: {pct_inst_s_parcelavel:.2f}% (Mín. 7.5% da área parc.) - {status_inst}<br>"
        
        # Validação Total APM (15% da Parcelável)
        status_total = "✅ OK" if pct_total_apm_s_parcelavel >= 15.0 else "❌ ABAIXO"
        summary_text += f"• Total APMs: {pct_total_apm_s_parcelavel:.2f}% (Mín. 15.0% da área parc.) - {status_total}<br>"
        
        summary_text += f"• <b>Total da área ocupada (Gleba Total): {pct_ocupacao_global:.2f}%</b><br>"
        
        if pct_total_apm_s_parcelavel < 15.0 or pct_verde_s_parcelavel < 7.5 or pct_inst_s_parcelavel < 7.5:
            summary_text += "<br><span style='color: red;'>⚠️ Atenção: O projeto não atende aos requisitos mínimos de APMs.</span>"
        else:
            summary_text += "<br><span style='color: green;'>✔️ O projeto atende aos requisitos do Plano Diretor de Goiânia.</span>"

        self.textSummary.setHtml(summary_text)

def run(iface):
    dialog = ProjectNormsDialog(iface, iface.mainWindow())
    dialog.show()
