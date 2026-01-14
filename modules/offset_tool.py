"""
/***************************************************************************
 RMCGeo
                                 A QGIS plugin
 Conjunto de ferramentas para simplificar tarefas geoespaciais.
                             -------------------
        begin                : 2025-10-26
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

from qgis.core import (
    Qgis, QgsWkbTypes, QgsGeometry, QgsPointXY, QgsFeature,
    QgsVectorLayer, QgsRectangle, QgsFeatureRequest, QgsMapLayerType,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
)
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QDoubleValidator


class OffsetDialog(QDialog):
    """Diálogo para entrada da distância do offset (apenas valores positivos)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Offset - Distância")
        self.setModal(True)
        self.distance = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Label de instrução
        instruction = QLabel(
            "Digite a distância do offset:\n"
            "(O lado será definido pela posição do mouse)"
        )
        layout.addWidget(instruction)
        
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Distância:"))
        
        self.distance_input = QLineEdit()
        self.distance_input.setPlaceholderText("Ex: 10.5")
        
        # Validador para aceitar apenas números decimais positivos
        validator = QDoubleValidator()
        validator.setDecimals(4)
        validator.setBottom(0.0001)
        self.distance_input.setValidator(validator)
        
        input_layout.addWidget(self.distance_input)
        layout.addLayout(input_layout)
        
        # Botões OK e Cancelar
        button_layout = QHBoxLayout()
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        self.distance_input.setFocus()
        
        self.distance_input.returnPressed.connect(self.accept)
    
    def accept(self):
        """Valida e aceita o input."""
        text = self.distance_input.text().strip()
        
        if not text:
            return
        
        try:
            self.distance = abs(float(text.replace(',', '.')))
            if self.distance <= 0:
                self.distance_input.setStyleSheet("background-color: #ffcccc;")
                return
            super().accept()
        except ValueError:
            self.distance_input.setStyleSheet("background-color: #ffcccc;")
    
    def get_distance(self):
        """Retorna a distância inserida."""
        return self.distance


class OffsetTool(QgsMapTool):
    """Ferramenta Offset - Cria uma linha paralela a uma distância especificada."""

    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.selected_feature = None
        self.selected_layer = None
        self.original_geometry = None
        self.offset_distance = None
        self.offset_side = 1
        self.is_selecting_feature = True
        self.is_selecting_side = False
        
        self.search_radius = 5
        self.hover_feature = None
        self.hover_layer = None
        
        try:
            self.setCursor(Qt.CursorShape.CrossCursor)  # Qt6
        except AttributeError:
            self.setCursor(Qt.CrossCursor)  # Qt5
        
        self.hover_rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.hover_rubber_band.setColor(QColor(255, 50, 50, 220))
        self.hover_rubber_band.setWidth(4)
        
        self.preview_rubber_band = self.create_rubber_band(
            QgsWkbTypes.LineGeometry, QColor(0, 150, 255, 180), 2
        )
    
    def activate(self):
        super().activate()
        
        # Verifica se a camada ativa é uma camada de linha
        active_layer = self.iface.activeLayer()
        if not active_layer or active_layer.type() != QgsMapLayerType.VectorLayer or \
           active_layer.geometryType() != QgsWkbTypes.LineGeometry:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Camada Inválida",
                "Por favor, selecione uma camada de linhas para trabalhar com o Offset."
            )
            # Desativa a ferramenta se a camada não for adequada
            self.canvas.unsetMapTool(self)
            return

        self.get_offset_distance()
    
    def get_offset_distance(self):
        dialog = OffsetDialog(self.iface.mainWindow())
        
        result = dialog.exec() if hasattr(dialog, 'exec') else dialog.exec_()
        
        try:
            accepted = QDialog.DialogCode.Accepted  # Qt6
        except AttributeError:
            accepted = QDialog.Accepted  # Qt5
        
        if result == accepted:
            distance = dialog.get_distance()
            
            if distance is not None and distance > 0:
                self.offset_distance = distance
            else:
                self.canvas.unsetMapTool(self)
        else:
            self.canvas.unsetMapTool(self)
    
    def canvasMoveEvent(self, event):
        """Atualiza o highlight visual e o preview do offset quando o mouse se move."""
        point = self.toMapCoordinates(event.pos())
        
        if self.is_selecting_feature:
            self.update_hover_highlight(point)
        
        elif self.is_selecting_side and self.original_geometry:
            point_in_layer_crs = self.transform_point_to_layer_crs(point, self.selected_layer)
            self.offset_side = calculate_offset_side(self.original_geometry, point_in_layer_crs)
            self.create_offset_preview()
    
    def canvasPressEvent(self, event):
        try:
            right_button = Qt.MouseButton.RightButton  # Qt6
            left_button = Qt.MouseButton.LeftButton  # Qt6
        except AttributeError:
            right_button = Qt.RightButton  # Qt5
            left_button = Qt.LeftButton  # Qt5
        
        if event.button() == right_button:
            self.reset_tool()
            self.canvas.unsetMapTool(self)
            return
        
        if event.button() == left_button:
            if self.is_selecting_feature:
                self.select_feature()
            
            elif self.is_selecting_side:
                self.create_offset_feature()
                self.reset_tool()
                self.is_selecting_feature = True
    
    def select_feature(self):
        """Seleciona a feição para aplicar o offset."""
        if not self.hover_feature or not self.hover_layer:
            return
        
        if not self.is_line_layer(self.hover_layer):
            return
        
        if not self.ensure_edit_mode(self.hover_layer):
            return
        
        self.selected_feature = self.hover_feature
        self.selected_layer = self.hover_layer
        self.original_geometry = self.hover_feature.geometry()
        
        self.is_selecting_feature = False
        self.is_selecting_side = True
        
        self.clear_hover_highlight()
    
    def create_offset_preview(self):
        """Cria o preview do offset baseado na distância e lado selecionados."""
        if not self.original_geometry or self.offset_distance is None:
            return
        
        try:
            distance = self.offset_distance * self.offset_side
            offset_geom = create_offset_geometry(
                self.original_geometry, 
                distance, 
                self.selected_layer.crs() if self.selected_layer else None
            )
            
            if offset_geom and not offset_geom.isEmpty():
                offset_geom_canvas = self.transform_geometry_to_canvas_crs(offset_geom, self.selected_layer)
                
                self.preview_rubber_band.reset(QgsWkbTypes.LineGeometry)
                self.preview_rubber_band.addGeometry(offset_geom_canvas)
            else:
                self.preview_rubber_band.reset()
        
        except Exception as e:
            print(f"Erro ao criar preview do offset: {str(e)}")
            self.preview_rubber_band.reset()
    
    def create_offset_feature(self):
        """Cria a nova feição com o offset."""
        if not self.original_geometry or not self.selected_layer or self.offset_distance is None:
            return
        
        try:
            distance = self.offset_distance * self.offset_side
            offset_geom = create_offset_geometry(
                self.original_geometry, 
                distance, 
                self.selected_layer.crs()
            )
            
            if not offset_geom or offset_geom.isEmpty():
                return
            
            # Copia os atributos da feição original (exceto o ID/FID para autogeração)
            attributes = {}
            pk_indices = self.selected_layer.primaryKeyAttributes()
            for i, field in enumerate(self.selected_layer.fields()):
                # Pula campos que são chaves primárias ou se chamam 'fid'/'id'
                if i in pk_indices or field.name().lower() in ['fid', 'id']:
                    continue
                field_name = field.name()
                attributes[field_name] = self.selected_feature[field_name]
            
            self.add_feature_to_layer(self.selected_layer, offset_geom, attributes)
        
        except Exception as e:
            pass
    
    def reset_tool(self):
        """Reseta a ferramenta para uma nova operação."""
        self.selected_feature = None
        self.selected_layer = None
        self.original_geometry = None
        self.offset_side = 1
        self.is_selecting_feature = True
        self.is_selecting_side = False
        self.preview_rubber_band.reset()
    
    def is_line_layer(self, layer):
        """Verifica se a camada é do tipo linha."""
        if not layer:
            return False
        
        return layer.geometryType() == QgsWkbTypes.LineGeometry
    
    def ensure_edit_mode(self, layer):
        """Verifica se a camada está em modo de edição."""
        if not layer:
            return False
        
        if not layer.isEditable():
            QMessageBox.warning(
                None,
                "Modo de Edição",
                "Por favor, habilite a edição da camada de linha antes de usar esta ferramenta."
            )
            return False
        
        return True
    
    def add_feature_to_layer(self, layer, geometry, attributes=None):
        """Adiciona uma nova feição à camada."""
        if not layer or not geometry:
            return False
        
        if not self.ensure_edit_mode(layer):
            return False
        
        feature = QgsFeature(layer.fields())
        feature.setGeometry(geometry)
        
        if attributes:
            for field_name, value in attributes.items():
                field_index = layer.fields().indexOf(field_name)
                if field_index >= 0:
                    feature.setAttribute(field_index, value)
        
        success = layer.addFeature(feature)
        
        if success:
            layer.updateExtents()
            layer.triggerRepaint()
            self.canvas.refresh()
        
        return success
    
    def create_rubber_band(self, geom_type=QgsWkbTypes.LineGeometry, color=None, width=2):
        """Cria um rubber band para preview visual."""
        rubber_band = QgsRubberBand(self.canvas, geom_type)
        
        if color is None:
            color = QColor(255, 0, 0, 180)
        
        rubber_band.setColor(color)
        rubber_band.setWidth(width)
        
        return rubber_band
    
    def clear_hover_highlight(self):
        """Limpa o highlight de hover."""
        if self.hover_rubber_band:
            self.hover_rubber_band.reset()
        self.hover_feature = None
        self.hover_layer = None
    
    def find_closest_line_at_point(self, point, layer=None):
        """Encontra a linha mais próxima de um ponto no mapa."""
        search_radius_map = self.canvas.mapSettings().mapUnitsPerPixel() * self.search_radius
        
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        
        closest_feature = None
        closest_layer = None
        closest_geom = None
        min_distance = float('inf')
        
        layers_to_search = [layer] if layer else self.canvas.layers()
        
        for search_layer in layers_to_search:
            if not isinstance(search_layer, QgsVectorLayer):
                continue
            
            if search_layer.type() != QgsMapLayerType.VectorLayer:
                continue
            
            if search_layer.geometryType() != QgsWkbTypes.LineGeometry:
                continue
            
            point_in_layer_crs = self.transform_point_to_layer_crs(point, search_layer)
            
            layer_crs = search_layer.crs()
            search_radius_layer = search_radius_map
            
            if canvas_crs != layer_crs:
                try:
                    point2 = QgsPointXY(point.x() + search_radius_map, point.y())
                    point2_in_layer = self.transform_point_to_layer_crs(point2, search_layer)
                    search_radius_layer = point_in_layer_crs.distance(point2_in_layer)
                except:
                    pass
            
            search_rect = QgsRectangle(
                point_in_layer_crs.x() - search_radius_layer,
                point_in_layer_crs.y() - search_radius_layer,
                point_in_layer_crs.x() + search_radius_layer,
                point_in_layer_crs.y() + search_radius_layer
            )
            
            for feature in search_layer.getFeatures(QgsFeatureRequest(search_rect)):
                geom = feature.geometry()
                if not geom:
                    continue
                
                point_geom = QgsGeometry.fromPointXY(point_in_layer_crs)
                distance = geom.distance(point_geom)
                
                if distance < min_distance and distance <= search_radius_layer:
                    min_distance = distance
                    closest_feature = feature
                    closest_layer = search_layer
                    closest_geom = geom
        
        return closest_feature, closest_layer, closest_geom
    
    def update_hover_highlight(self, point):
        """Atualiza o highlight visual da linha sob o mouse."""
        # Busca a linha mais próxima apenas na camada ativa selecionada pelo usuário
        active_layer = self.iface.activeLayer()
        
        # Se não houver camada ativa ou não for uma camada de vetor de linha, limpa e retorna
        if not active_layer or active_layer.type() != QgsMapLayerType.VectorLayer or \
           active_layer.geometryType() != QgsWkbTypes.LineGeometry:
            self.clear_hover_highlight()
            return

        # Busca a feição mais próxima apenas na camada ativa
        feature, layer, geom = self.find_closest_line_at_point(point, active_layer)
        
        if feature and geom:
            geom_in_canvas_crs = self.transform_geometry_to_canvas_crs(geom, layer)
            
            self.hover_rubber_band.reset(QgsWkbTypes.LineGeometry)
            self.hover_rubber_band.addGeometry(geom_in_canvas_crs)
            self.hover_feature = feature
            self.hover_layer = layer
        else:
            self.clear_hover_highlight()
    
    def transform_point_to_layer_crs(self, point, layer):
        """Transforma um ponto do CRS do canvas para o CRS da camada."""
        if not layer:
            return point
        
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        layer_crs = layer.crs()
        
        if canvas_crs == layer_crs:
            return point
        
        try:
            transform = QgsCoordinateTransform(canvas_crs, layer_crs, QgsProject.instance())
            return transform.transform(point)
        except Exception as e:
            print(f"Erro ao transformar ponto: {str(e)}")
            return point
    
    def transform_geometry_to_canvas_crs(self, geometry, layer):
        """Transforma uma geometria do CRS da camada para o CRS do canvas."""
        if not layer or not geometry:
            return geometry
        
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        layer_crs = layer.crs()
        
        if canvas_crs == layer_crs:
            return geometry
        
        try:
            geom_copy = QgsGeometry(geometry)
            transform = QgsCoordinateTransform(layer_crs, canvas_crs, QgsProject.instance())
            result = geom_copy.transform(transform)
            if result == 0:
                return geom_copy
            else:
                return geometry
        except Exception as e:
            print(f"Erro ao transformar geometria: {str(e)}")
            return geometry
    
    def deactivate(self):
        self.reset_tool()
        self.preview_rubber_band.reset()
        self.clear_hover_highlight()
        super().deactivate()


def create_offset_geometry(geometry, distance, source_crs=None):
    """Cria uma geometria paralela (offset) a uma distância especificada, preservando a forma."""
    if not geometry:
        return None

    try:
        # Determinar se precisamos converter para um CRS projetado
        needs_conversion = False
        transform_to_projected = None
        transform_from_projected = None
        working_geom = geometry
        working_crs = source_crs
        
        if source_crs and source_crs.isGeographic():
            needs_conversion = True
            
            centroid = geometry.centroid().asPoint()
            
            # Calcular zona UTM baseada na longitude
            longitude = centroid.x()
            utm_zone = int((longitude + 180) / 6) + 1
            
            latitude = centroid.y()
            is_south = latitude < 0
            
            # Construir código EPSG para zona UTM WGS84
            # Zonas Norte: 32601-32660, Zonas Sul: 32701-32760
            if is_south:
                epsg_code = 32700 + utm_zone
            else:
                epsg_code = 32600 + utm_zone
            
            utm_crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg_code}")
            
            if not utm_crs.isValid():
                utm_crs = QgsCoordinateReferenceSystem("EPSG:31982")
            
            working_crs = utm_crs
            
            transform_to_projected = QgsCoordinateTransform(
                source_crs, 
                utm_crs, 
                QgsProject.instance()
            )
            transform_from_projected = QgsCoordinateTransform(
                utm_crs, 
                source_crs, 
                QgsProject.instance()
            )
            
            working_geom = QgsGeometry(geometry)
            result = working_geom.transform(transform_to_projected)
            
            if result != 0:
                print(f"Erro ao transformar geometria para CRS projetado")
                return None
        
        geom_type = working_geom.type()

        def _is_closed_line(geom: QgsGeometry) -> bool:
            if geom.isMultipart():
                parts = geom.asMultiPolyline()
                if not parts:
                    return False
                ring = parts[0]
            else:
                ring = geom.asPolyline()
            if len(ring) < 3:
                return False
            first, last = ring[0], ring[-1]
            return abs(first.x() - last.x()) < 1e-9 and abs(first.y() - last.y()) < 1e-9

        if geom_type == QgsWkbTypes.PolygonGeometry or (geom_type == QgsWkbTypes.LineGeometry and _is_closed_line(working_geom)):
            poly_geom = None

            if geom_type == QgsWkbTypes.PolygonGeometry:
                poly_geom = working_geom
            else:
                if working_geom.isMultipart():
                    ring = working_geom.asMultiPolyline()[0]
                else:
                    ring = working_geom.asPolyline()
                if ring[0] != ring[-1]:
                    ring = ring + [ring[0]]
                poly_geom = QgsGeometry.fromPolygonXY([ring])

            buffered = poly_geom.buffer(
                distance,
                segments=1,
                endCapStyle=Qgis.EndCapStyle.Flat,
                joinStyle=Qgis.JoinStyle.Miter,
                miterLimit=10.0,
            )

            if not buffered or buffered.isEmpty():
                return None

            if buffered.isMultipart():
                polygons = buffered.asMultiPolygon()
                if not polygons:
                    return None
                exterior_ring = polygons[0][0]
            else:
                polygon = buffered.asPolygon()
                if not polygon:
                    return None
                exterior_ring = polygon[0]
            
            boundary_line = QgsGeometry.fromPolylineXY(exterior_ring)
            
            if not boundary_line or boundary_line.isEmpty():
                return None

            offset_geom = boundary_line
        else:
            offset_geom = working_geom.offsetCurve(
                distance,
                segments=8,
                joinStyle=Qgis.JoinStyle.Miter,
                miterLimit=10.0,
            )

            if not offset_geom or offset_geom.isEmpty():
                return None
        
        if needs_conversion and transform_from_projected:
            result = offset_geom.transform(transform_from_projected)
            if result != 0:
                print(f"Erro ao transformar geometria de volta para o CRS original")
                return None

        return offset_geom

    except Exception as e:
        print(f"Erro ao criar offset: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def calculate_offset_side(geometry, mouse_point):
    """Calcula o lado do offset baseado na posição do mouse em relação à linha."""

    if not geometry or not mouse_point:
        return 1
    
    if geometry.isMultipart():
        vertices = geometry.asMultiPolyline()[0]
    else:
        vertices = geometry.asPolyline()
    
    if len(vertices) < 2:
        return 1
    
    min_distance = float('inf')
    closest_segment = None
    
    for i in range(len(vertices) - 1):
        seg_start = vertices[i]
        seg_end = vertices[i + 1]
        
        # Calcula distância do mouse ao segmento
        segment = QgsGeometry.fromPolylineXY([seg_start, seg_end])
        mouse_geom = QgsGeometry.fromPointXY(mouse_point)
        distance = segment.distance(mouse_geom)
        
        if distance < min_distance:
            min_distance = distance
            closest_segment = (seg_start, seg_end)
    
    if not closest_segment:
        return 1
    
    seg_start, seg_end = closest_segment
    
    cross_product = (
        (mouse_point.x() - seg_start.x()) * (seg_end.y() - seg_start.y()) -
        (mouse_point.y() - seg_start.y()) * (seg_end.x() - seg_start.x())
    )
    
    return -1 if cross_product > 0 else 1


def run(iface):
    canvas = iface.mapCanvas()
    tool = OffsetTool(canvas, iface)
    canvas.setMapTool(tool)