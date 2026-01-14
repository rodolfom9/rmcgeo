"""
/***************************************************************************
 RMCGeo
                                 A QGIS plugin
 Conjunto de ferramentas para simplificar tarefas geoespaciais.
                             -------------------
        begin                : 2025-11-25
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

import webbrowser
from qgis.PyQt.QtWidgets import QAction, QMenu
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.PyQt.QtCore import QUrl, QCoreApplication


# ========================================
# 🔗 CONFIGURAÇÃO DE LINKS
# ========================================
# Adicione ou remova links diretamente aqui!
# Para adicionar um novo link, siga o padrão abaixo.

LINKS_UTEIS = [
    {
        "categoria": "Base de Dados",
        "links": [
            {
                "nome": "IBGE - RBMC",
                "url": "https://www.ibge.gov.br/geociencias/informacoes-sobre-posicionamento-geodesico/rede-geodesica/16258-rede-brasileira-de-monitoramento-continuo-dos-sistemas-gnss-rbmc.html?=&t=dados-diarios-e-situacao-operacional",
                "descricao": "Situação operacional RBMC"
            },
            {
                "nome": "IBGE - Downloads",
                "url": "https://www.ibge.gov.br/geociencias/downloads-geociencias.html",
                "descricao": "Downloads de dados geográficos"
            },
            {
                "nome": "IBGE - Mapas",
                "url": "https://mapas.ibge.gov.br/",
                "descricao": "Visualizador de mapas interativo"
            },
            {
                "nome": "IBGE - PPP",
                "url": "https://www.ibge.gov.br/geociencias/informacoes-sobre-posicionamento-geodesico/servicos-para-posicionamento-geodesico/16334-servico-online-para-pos-processamento-de-dados-gnss-ibge-ppp.html?=&t=processar-os-dados",
                "descricao": "Serviço online para pós-processamento de dados GNSS"
            },
            {
                "nome": "INPE - Terrabrasilis",
                "url": "http://terrabrasilis.dpi.inpe.br/",
                "descricao": "Plataforma de dados geoespaciais do INPE"
            },
            {
                "nome": "INDE - IDE Brasil",
                "url": "https://www.inde.gov.br/",
                "descricao": "Infraestrutura Nacional de Dados Espaciais"
            }
        ]
    },
    {
        "categoria": "INCRA",
        "links": [
            {
                "nome": "INCRA - SIGEF",
                "url": "https://sigef.incra.gov.br/",
                "descricao": "Sistema de Gestão Fundiária"
            },
            {
                "nome": "INCRA - Acervo Fundiário",
                "url": "https://acervofundiario.incra.gov.br/",
                "descricao": "Acervo de documentos fundiários"
            },
            {
                "nome": "Normas Técnicas de Georreferenciamento - INCRA",
                "url": "https://www.gov.br/incra/pt-br/assuntos/governanca-fundiaria/georreferenciamento",
                "descricao": "Normas para georreferenciamento de imóveis rurais"
            },
            {
                "nome": "Lei 10.267/2001",
                "url": "http://www.planalto.gov.br/ccivil_03/leis/leis_2001/l10267.htm",
                "descricao": "Lei do georreferenciamento de imóveis rurais"
            }
        ]
    },
    {
        "categoria": "Imagens de Satélite",
        "links": [
            {
                "nome": "EarthExplorer - USGS",
                "url": "https://earthexplorer.usgs.gov/",
                "descricao": "Download de imagens Landsat e outros"
            },
            {
                "nome": "Sentinel Hub",
                "url": "https://www.sentinel-hub.com/",
                "descricao": "Imagens Sentinel e outros satélites"
            },
            {
                "nome": "Google Earth Engine",
                "url": "https://earthengine.google.com/",
                "descricao": "Plataforma de análise geoespacial"
            }
        ]
    },
    {
        "categoria": "Ferramentas Online",
        "links": [
            {
                "nome": "IBGE - ProGrid",
                "url": "https://www.ibge.gov.br/geociencias/informacoes-sobre-posicionamento-geodesico/servicos-para-posicionamento-geodesico/16312-calculadora-geodesica.html",
                "descricao": "Calculadora para coordenadas geodésicas"
            },
            {
                "nome": "Conversor de Coordenadas",
                "url": "https://www.latlong.net/",
                "descricao": "Conversor online de coordenadas"
            },
            {
                "nome": "NOAA - Magnetic Declination",
                "url": "https://www.ngdc.noaa.gov/geomag/calculators/magcalc.shtml",
                "descricao": "Cálculo da declinação magnética para bússolas."
            }
        ]
    }
]

# ========================================
# Para adicionar novos links, basta copiar e colar este modelo:
#
#    {
#        "categoria": "Nome da Categoria",
#        "links": [
#            {
#                "nome": "Nome do Link",
#                "url": "https://exemplo.com",
#                "descricao": "Descrição do link"
#            },
#            {
#                "nome": "Outro Link",
#                "url": "https://exemplo2.com",
#                "descricao": "Outra descrição"
#            }
#        ]
#    },
#
# ========================================


class LinksUteisManager:
    """Gerenciador de links úteis."""
    
    def __init__(self, plugin_dir=None):
        """Inicializa o gerenciador de links."""
        self.links = LINKS_UTEIS

    def tr(self, message):
        """Get the translation for a string using Qt translation API."""
        return QCoreApplication.translate('RMCGeo', message)
    
    def open_link(self, url):
        """Abre um link no navegador padrão."""
        try:
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            print(f"Erro ao abrir link: {e}")
            # Fallback para webbrowser
            try:
                webbrowser.open(url)
            except:
                pass
    
    def create_menu_actions(self, parent_menu, iface):
        """
        Cria as ações de menu dinamicamente baseado nos links.
        
        Args:
            parent_menu: Menu pai onde os links serão adicionados
            iface: Interface do QGIS
        
        Returns:
            Lista de ações criadas
        """
        actions = []
        
        if not self.links:
            # Sem links, mostrar mensagem
            no_links_action = QAction(self.tr("No links configured"), iface.mainWindow())
            no_links_action.setEnabled(False)
            parent_menu.addAction(no_links_action)
            actions.append(no_links_action)
            return actions
        
        # Agrupar por categoria
        for categoria_data in self.links:
            categoria = categoria_data.get('categoria', 'Sem Categoria')
            links_categoria = categoria_data.get('links', [])
            
            if not links_categoria:
                continue
            
            # Criar submenu para cada categoria
            submenu = QMenu(self.tr(categoria), parent_menu)
            submenu.setIcon(QIcon(':/images/themes/default/mIconFolder.svg'))
            parent_menu.addMenu(submenu)
            
            # Adicionar links da categoria
            for link_data in links_categoria:
                nome = link_data.get('nome', 'Link')
                url = link_data.get('url', '')
                descricao = link_data.get('descricao', '')
                
                if not url:
                    continue
                
                # Criar ação para o link
                action = QAction(
                    QIcon(':/images/themes/default/mIconWms.svg'),
                    self.tr(nome),
                    iface.mainWindow()
                )
                
                if descricao:
                    translated_desc = self.tr(descricao)
                    action.setStatusTip(translated_desc)
                    action.setToolTip(translated_desc)
                
                # Conectar ação para abrir o link
                # Usar lambda com argumento padrão para capturar o URL correto
                action.triggered.connect(lambda checked=False, u=url: self.open_link(u))
                
                submenu.addAction(action)
                actions.append(action)
        
        return actions


def run(iface):
    """Função de compatibilidade (não usada diretamente)."""
    pass
