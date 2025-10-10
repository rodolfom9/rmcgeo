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

from qgis.PyQt.QtWidgets import QMessageBox, QDialog
from qgis.PyQt import uic
from qgis.core import (QgsProject,QgsField,QgsExpression,QgsExpressionContext,
                        QgsExpressionContextUtils,QgsWkbTypes,QgsVectorLayer)
from qgis.PyQt.QtCore import QVariant
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import os

# Carrega o arquivo .ui
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '..', 'ui', 'coluna_tabela.ui'))


class BaseCalculadoraTabela(QDialog, FORM_CLASS):
    """Classe base para criar ferramentas que adicionam campos calculados
    nas tabelas de atributos das camadas."""
    
    # Configurações padrão (devem ser sobrescritas nas subclasses)
    window_title = "Adicionar Campo na Tabela"
    field_name = "NovoCampo"
    field_type = QVariant.Double
    expression_string = "$area"
    geometry_types = None  # None = aceita todos os tipos
    format_options = None  # None = sem opções de formatação, ou dicionário
    field_names_by_format = None  # None = nome fixo, ou dicionário
    
    def __init__(self, iface):
        super().__init__()
        self.setupUi(self)
        self.iface = iface
        
        # Carrega o ícone
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'icon.svg')
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            self.icon.setPixmap(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        # Configura a interface
        self.setWindowTitle(self.window_title)
        self.select_camada.setText("Selecione a Camada:")
        self.status_label.setText("Status: Aguardando seleção")
        
        # Configura o combo de formatação
        self.configurar_formatacao_combo()
        
        # Preenche o combo box com as camadas
        self.popular_camadas()
        
        # Conecta o botão salvar
        self.salvarButton.clicked.connect(self.add_campo)
        
        # Conecta a mudança de camada
        self.coluna_combo.currentIndexChanged.connect(self.ao_mudar_camada)
        
        # Conecta a mudança de formato
        self.formatacao_combo.currentIndexChanged.connect(self.ao_mudar_formato)
    
    def configurar_formatacao_combo(self):
        """Configura o combo box de formatação"""
        self.formatacao_combo.clear()
        
        if self.format_options:
            for format_name in self.format_options.keys():
                self.formatacao_combo.addItem(format_name)
            self.formatacao_combo.setEnabled(True)
        else:
            self.formatacao_combo.addItem("Padrão")
            self.formatacao_combo.setEnabled(False)
    
    def ao_mudar_formato(self):
        """Atualiza quando o formato é alterado"""
        if self.format_options:
            selected_format = self.formatacao_combo.currentText()
            
            # Atualiza o nome do campo se houver mapeamento definido
            if self.field_names_by_format and selected_format in self.field_names_by_format:
                self.field_name = self.field_names_by_format[selected_format]
            
            self.status_label.setText(f"Status: Formato selecionado - {selected_format}")
    
    def nome_tipo_geometria(self, geom_type):
        """Retorna o nome legível do tipo de geometria"""
        if geom_type == QgsWkbTypes.PointGeometry:
            return "pontos"
        elif geom_type == QgsWkbTypes.LineGeometry:
            return "linhas"
        elif geom_type == QgsWkbTypes.PolygonGeometry:
            return "polígonos"
        return "geometrias"
    
    def popular_camadas(self):
        """Preenche o combo box com as camadas compatíveis do projeto"""
        self.coluna_combo.clear()
        
        layers = QgsProject.instance().mapLayers().values()
        compatible_layers = []
        
        for layer in layers:
            if not isinstance(layer, QgsVectorLayer):
                continue
            
            # Se geometry_types foi definido, filtra por tipo
            if self.geometry_types is not None:
                if layer.geometryType() in self.geometry_types:
                    compatible_layers.append(layer)
            else:
                # Aceita todas as camadas vetoriais
                compatible_layers.append(layer)
        
        if not compatible_layers:
            if self.geometry_types:
                geom_names = [self.nome_tipo_geometria(gt) for gt in self.geometry_types]
                geom_text = ", ".join(geom_names)
                self.status_label.setText(f"Status: Nenhuma camada de {geom_text} encontrada")
            else:
                self.status_label.setText("Status: Nenhuma camada vetorial encontrada")
            self.salvarButton.setEnabled(False)
            return
        
        for layer in compatible_layers:
            self.coluna_combo.addItem(layer.name(), layer)
        
        self.salvarButton.setEnabled(True)
        self.ao_mudar_camada()
    
    def ao_mudar_camada(self):
        """Atualiza o status quando a camada é alterada"""
        if self.coluna_combo.count() > 0:
            layer = self.coluna_combo.currentData()
            if layer:
                feature_count = layer.featureCount()
                self.status_label.setText(f"Status: {feature_count} feições na camada")
    
    def formatar_valor(self, value):
        """Formata o valor retornado pela expressão."""
        if isinstance(value, str):
            try:
                return float(value.replace(',', '.'))
            except:
                return value
        return value
    
    def validar_camada_selecionada(self):
        """Valida se há uma camada selecionada"""
        if self.coluna_combo.count() == 0:
            QMessageBox.warning(
                self,
                "Aviso",
                "Nenhuma camada compatível disponível!"
            )
            return None
        
        layer = self.coluna_combo.currentData()
        if not layer:
            QMessageBox.warning(
                self,
                "Aviso",
                "Por favor, selecione uma camada!"
            )
            return None
        
        return layer
    
    def obter_expressao_calculo(self):
        """Obtém a expressão de cálculo baseada no formato selecionado"""
        if self.format_options:
            selected_format = self.formatacao_combo.currentText()
            return self.format_options[selected_format]
        else:
            return self.expression_string
    
    def verificar_campo_existente(self, layer):
        """Verifica se o campo já existe e pergunta ao usuário se deseja recalcular"""
        field_names = [field.name() for field in layer.fields()]
        if self.field_name in field_names:
            reply = QMessageBox.question(
                self,
                "Campo já existe",
                f"O campo '{self.field_name}' já existe na camada.\nDeseja recalcular os valores?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return None
            return True
        return False
    
    def criar_campo(self, layer):
        """Cria o campo na camada se não existir"""
        field = QgsField(self.field_name, self.field_type)
        # Define tamanho para campos String
        if self.field_type == QVariant.String:
            field.setLength(254)
        layer.addAttribute(field)
        layer.updateFields()
    
    def preparar_expressao(self, layer, expression_string):
        """Prepara e valida a expressão QGIS"""
        expression = QgsExpression(expression_string)
        context = QgsExpressionContext()
        context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        expression.prepare(context)
        
        if expression.hasParserError():
            raise Exception(f"Erro na expressão: {expression.parserErrorString()}")
        
        return expression, context
    
    def calcular_valores_feicoes(self, layer, expression, context, field_index):
        """Calcula e atualiza os valores para todas as feições"""
        feature_count = 0
        error_count = 0
        for feature in layer.getFeatures():
            context.setFeature(feature)
            value = expression.evaluate(context)
            
            # Verifica se houve erro na avaliação
            if expression.hasEvalError():
                error_count += 1
                if error_count == 1:  # Mostra apenas o primeiro erro
                    raise Exception(f"Erro ao calcular valor: {expression.evalErrorString()}")
            
            value = self.formatar_valor(value)
            layer.changeAttributeValue(feature.id(), field_index, value)
            feature_count += 1
        return feature_count
    
    def mostrar_resultado(self, field_exists, feature_count):
        """Mostra mensagem de sucesso ao usuário"""
        self.status_label.setText(f"Status: Concluído - {feature_count} feições processadas")
        QMessageBox.information(
            self,
            "Sucesso",
            f"Campo '{self.field_name}' {'atualizado' if field_exists else 'adicionado'} com sucesso!\n"
            f"{feature_count} feições processadas."
        )
    
    def add_campo(self):
        """Adiciona o campo calculado na camada selecionada"""
        # Valida a camada
        layer = self.validar_camada_selecionada()
        if not layer:
            return
        
        # Obtém a expressão
        current_expression = self.obter_expressao_calculo()
        
        # Verifica se o campo já existe
        field_exists = self.verificar_campo_existente(layer)
        if field_exists is None:  # Usuário cancelou
            return
        
        # Atualiza o status
        self.status_label.setText("Status: Processando...")
        
        # Verifica se a camada já está em modo de edição
        was_editing = layer.isEditable()
        
        # Inicia a edição da camada se não estiver editando
        if not was_editing:
            layer.startEditing()
        
        try:
            # Cria o campo se não existir
            if not field_exists:
                self.criar_campo(layer)
            
            # Obtém o índice do campo
            field_index = layer.fields().indexFromName(self.field_name)
            
            # Prepara a expressão
            expression, context = self.preparar_expressao(layer, current_expression)
            
            # Calcula os valores
            feature_count = self.calcular_valores_feicoes(layer, expression, context, field_index)
            
            # Mostra resultado
            self.mostrar_resultado(field_exists, feature_count)
            
            # Atualiza a camada
            layer.triggerRepaint()
            self.iface.mapCanvas().refresh()
            
        except Exception as e:
            # Em caso de erro, desfaz as alterações
            layer.rollBack()
            self.status_label.setText("Status: Erro no processamento")
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao adicionar/atualizar o campo:\n{str(e)}"
            )
