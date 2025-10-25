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
    Qgis, QgsWkbTypes, QgsGeometry, QgsPointXY,
    QgsVectorLayer, QgsRectangle, QgsFeatureRequest, QgsMapLayerType,
    QgsCoordinateTransform, QgsProject
)
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QMessageBox


class ExtendTool(QgsMapTool):
    
    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.line_to_extend = None
        self.line_to_extend_layer = None
        self.target_line = None
        self.target_line_layer = None
        self.step = 0
        self.mouse_position = None
        
        self.search_radius = 10
        self.hover_feature = None
        self.hover_layer = None
        
        try:
            self.setCursor(Qt.CursorShape.CrossCursor)  # Qt6
        except AttributeError:
            self.setCursor(Qt.CrossCursor)  # Qt5
        
        self.hover_rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.hover_rubber_band.setColor(QColor(255, 0, 0, 180))
        self.hover_rubber_band.setWidth(3)
        
        self.selected_rubber_band = self.create_rubber_band(
            QgsWkbTypes.LineGeometry, QColor(0, 255, 0, 180), 3
        )
        
        self.preview_rubber_band = self.create_rubber_band(
            QgsWkbTypes.LineGeometry, QColor(0, 150, 255, 150), 2
        )
    
    def canvasMoveEvent(self, event):
        point = self.toMapCoordinates(event.pos())
        self.mouse_position = point
        self.update_hover_highlight(point)
        
        if self.step == 1 and self.line_to_extend and self.hover_feature:
            if (self.hover_layer == self.line_to_extend_layer and 
                self.hover_feature.id() == self.line_to_extend.id()):
                return
            
            point_in_layer_crs = self.transform_point_to_layer_crs(point, self.line_to_extend_layer)
            
            hover_geom = self.hover_feature.geometry()
            if self.line_to_extend_layer.crs() != self.hover_layer.crs():
                try:
                    hover_geom = QgsGeometry(self.hover_feature.geometry())
                    transform = QgsCoordinateTransform(
                        self.hover_layer.crs(),
                        self.line_to_extend_layer.crs(),
                        QgsProject.instance()
                    )
                    hover_geom.transform(transform)
                except Exception as e:
                    print(f"Erro ao transformar geometria hover: {str(e)}")
                    return
            
            self.create_extend_preview_by_mouse_side(
                self.line_to_extend.geometry(),
                hover_geom,
                point_in_layer_crs
            )
    
    def canvasPressEvent(self, event):
        try:
            right_button = Qt.MouseButton.RightButton  # Qt6
            left_button = Qt.MouseButton.LeftButton  # Qt6
        except AttributeError:
            right_button = Qt.RightButton  # Qt5
            left_button = Qt.LeftButton  # Qt5
        
        if event.button() == right_button:
            return
        
        if event.button() != left_button:
            return
        
        if not self.hover_feature or not self.hover_layer:
            return
        
        # Verifica se a camada está em modo de edição (apenas para a primeira linha)
        if self.step == 0:
            if not self.is_line_layer(self.hover_layer):
                return
            
            if not self.ensure_edit_mode(self.hover_layer):
                return
            
            self.line_to_extend = self.hover_feature
            self.line_to_extend_layer = self.hover_layer
            self.step = 1
            
            geom_canvas = self.transform_geometry_to_canvas_crs(
                self.hover_feature.geometry(), 
                self.hover_layer
            )
            self.selected_rubber_band.reset(QgsWkbTypes.LineGeometry)
            self.selected_rubber_band.addGeometry(geom_canvas)
            
        elif self.step == 1:
            if not self.is_line_layer(self.hover_layer):
                return
            
            self.target_line = self.hover_feature
            self.target_line_layer = self.hover_layer
            self.perform_extend()
            self.reset_tool()
    
    def determine_extend_side(self, line_geom, mouse_point):
        if line_geom.isMultipart():
            points = line_geom.asMultiPolyline()[0]
        else:
            points = line_geom.asPolyline()
        
        if len(points) < 2:
            return 'end'
        
        first_point = points[0]
        last_point = points[-1]
        
        dx = last_point.x() - first_point.x()
        dy = last_point.y() - first_point.y()
        
        mouse_dx = mouse_point.x() - first_point.x()
        mouse_dy = mouse_point.y() - first_point.y()
        
        cross = dx * mouse_dy - dy * mouse_dx
        
        dot = dx * mouse_dx + dy * mouse_dy
        line_length_sq = dx * dx + dy * dy
        
        if line_length_sq > 0:
            t = dot / line_length_sq
            
            if t < 0.5:
                return 'start'
            else:
                return 'end'
        
        return 'end'
    
    def extend_line_from_side(self, line_geom, target_geom, side):
        """Estende a linha a partir de um lado específico até intersectar a linha alvo."""
        if line_geom.isMultipart():
            points = line_geom.asMultiPolyline()[0]
        else:
            points = line_geom.asPolyline()
        
        if len(points) < 2:
            return None
        
        first_point = points[0]
        last_point = points[-1]
        
        if side == 'end':
            p_before_last = points[-2] if len(points) > 1 else first_point
            dx = last_point.x() - p_before_last.x()
            dy = last_point.y() - p_before_last.y()
            
            extension_factor = 10000
            extended_point = QgsPointXY(
                last_point.x() + dx * extension_factor,
                last_point.y() + dy * extension_factor
            )
            
            extended_geom = QgsGeometry.fromPolylineXY([last_point, extended_point])
            intersection = self.find_line_intersection(extended_geom, target_geom)
            
            if intersection:
                new_points = list(points)
                new_points.append(intersection)
                return QgsGeometry.fromPolylineXY(new_points)
        
        else:
            p_after_first = points[1] if len(points) > 1 else last_point
            dx = first_point.x() - p_after_first.x()
            dy = first_point.y() - p_after_first.y()
            
            extension_factor = 10000
            extended_point = QgsPointXY(
                first_point.x() + dx * extension_factor,
                first_point.y() + dy * extension_factor
            )
            
            extended_geom = QgsGeometry.fromPolylineXY([first_point, extended_point])
            intersection = self.find_line_intersection(extended_geom, target_geom)
            
            if intersection:
                new_points = [intersection] + list(points)
                return QgsGeometry.fromPolylineXY(new_points)
        
        return None
    
    def create_extend_preview_by_mouse_side(self, line_geom, target_geom, mouse_point):
        """Cria preview da extensão baseado no lado do mouse (estilo AutoCAD).
        O lado do mouse determina qual extremidade estender."""

        # Limpa preview anterior
        self.preview_rubber_band.reset()
        
        side = self.determine_extend_side(line_geom, mouse_point)
        
        extended_geom = self.extend_line_from_side(line_geom, target_geom, side)
        
        if extended_geom and not extended_geom.isEmpty():
            extended_geom_canvas = self.transform_geometry_to_canvas_crs(
                extended_geom, 
                self.line_to_extend_layer
            )
            
            self.preview_rubber_band.reset(QgsWkbTypes.LineGeometry)
            self.preview_rubber_band.addGeometry(extended_geom_canvas)
    
    def perform_extend(self):
        """Executa a operação de extensão da linha baseado no lado do mouse."""
        if not self.line_to_extend or not self.target_line or not self.mouse_position:
            return
        
        if not self.line_to_extend_layer or not self.target_line_layer:
            return
        
        line_geom = self.line_to_extend.geometry()
        target_geom = self.target_line.geometry()
        
        if not line_geom or not target_geom:
            return
        
        if (self.line_to_extend_layer == self.target_line_layer and 
            self.line_to_extend.id() == self.target_line.id()):
            return
        
        mouse_in_layer_crs = self.transform_point_to_layer_crs(
            self.mouse_position, 
            self.line_to_extend_layer
        )
        
        target_geom_in_line_crs = target_geom
        if self.line_to_extend_layer.crs() != self.target_line_layer.crs():
            try:
                target_geom_in_line_crs = QgsGeometry(target_geom)
                transform = QgsCoordinateTransform(
                    self.target_line_layer.crs(),
                    self.line_to_extend_layer.crs(),
                    QgsProject.instance()
                )
                result = target_geom_in_line_crs.transform(transform)
                if result != 0:
                    print("Erro ao transformar geometria alvo")
                    return
            except Exception as e:
                print(f"Erro na transformação de CRS: {str(e)}")
                return
        
        side = self.determine_extend_side(line_geom, mouse_in_layer_crs)
        extended_geom = self.extend_line_from_side(line_geom, target_geom_in_line_crs, side)
        
        if not extended_geom or extended_geom.equals(line_geom):
            return
        
        self.update_feature_geometry(self.line_to_extend_layer, self.line_to_extend, extended_geom)
    
    def reset_tool(self):
        self.line_to_extend = None
        self.line_to_extend_layer = None
        self.target_line = None
        self.target_line_layer = None
        self.mouse_position = None
        self.step = 0
        self.clear_rubber_band()
        self.selected_rubber_band.reset()
        self.preview_rubber_band.reset()
    
    def canvasReleaseEvent(self, event):
        """Captura quando o botão do mouse é solto."""
        # Compatibilidade Qt5/Qt6: MouseButton enum
        try:
            right_button = Qt.MouseButton.RightButton  # Qt6
        except AttributeError:
            right_button = Qt.RightButton  # Qt5
        
        if event.button() == right_button:
            self.reset_tool()
            self.canvas.unsetMapTool(self)
    
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
    
    def find_line_intersection(self, geom1, geom2):
        """Encontra o ponto de interseção entre duas geometrias de linha."""
        if not geom1 or not geom2:
            return None
        
        intersection = geom1.intersection(geom2)
        
        if intersection.isEmpty():
            return None
        
        if intersection.type() == QgsWkbTypes.PointGeometry:
            if intersection.isMultipart():
                points = intersection.asMultiPoint()
                if points:
                    return points[0]
            else:
                return intersection.asPoint()
        
        return None
    
    def update_feature_geometry(self, layer, feature, new_geometry):
        """Atualiza a geometria de uma feição na camada."""
        if not layer or not feature or not new_geometry:
            return False
        
        if not self.ensure_edit_mode(layer):
            return False
        
        success = layer.changeGeometry(feature.id(), new_geometry)
        
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
    
    def clear_rubber_band(self):
        """Limpa o rubber band atual."""
        if hasattr(self, 'rubber_band') and self.rubber_band:
            self.rubber_band.reset()
            self.rubber_band = None
    
    def clear_hover_highlight(self):
        """Limpa o highlight de hover."""
        if self.hover_rubber_band:
            self.hover_rubber_band.reset()
        self.hover_feature = None
        self.hover_layer = None
    
    def find_closest_line_at_point(self, point, layer=None):
        """Encontra a linha mais próxima de um ponto no mapa."""
        # Converte o raio de busca de pixels para unidades do mapa
        search_radius_map = self.canvas.mapSettings().mapUnitsPerPixel() * self.search_radius
        
        # Obtém o CRS do canvas
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
                
                if distance < min_distance and distance < search_radius_layer:
                    min_distance = distance
                    closest_feature = feature
                    closest_layer = search_layer
                    closest_geom = geom
        
        return closest_feature, closest_layer, closest_geom
    
    def update_hover_highlight(self, point):
        """Atualiza o highlight visual da linha sob o mouse."""
        
        feature, layer, geom = self.find_closest_line_at_point(point)
        
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
        self.preview_rubber_band.reset()
        self.clear_hover_highlight()
        self.reset_tool()
        super().deactivate()


def run(iface):
    canvas = iface.mapCanvas()
    tool = ExtendTool(canvas, iface)
    canvas.setMapTool(tool)
    
    iface.messageBar().pushMessage(
        "Ferramenta Extend",
        "Clique na linha que deseja estender. A linha pode estar em qualquer camada/CRS.",
        level=Qgis.Info,
        duration=5
    )