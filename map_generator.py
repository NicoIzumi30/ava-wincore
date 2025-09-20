import folium
from folium import plugins
from folium.plugins import MarkerCluster
from geopy.distance import geodesic
import os
import requests
import json
from datetime import datetime
from config import DEFAULT_OUTPUT_MAP, logger, PROVINCE_BOUNDS, get_province_map_filename, CLUSTERING_SETTINGS
from api_handler import get_nearby_places_detail
from multi_province_utils import (
    group_outlets_by_province, create_province_navigation, create_province_info_panel,
    save_province_map_metadata, validate_province_data
)
from indomaret_handler import IndomaretHandler

# Data boundary provinsi Indonesia yang disesuaikan dengan requirement (hanya 5 provinsi dengan data)
INDONESIA_PROVINCES = PROVINCE_BOUNDS

def get_province_from_coordinates(lat, lon):
    """
    Menentukan provinsi berdasarkan koordinat dengan akurasi tinggi
    Disesuaikan dengan 5 provinsi target
    """
    # Cek exact match terlebih dahulu
    for province, data in INDONESIA_PROVINCES.items():
        bounds = data['bounds']
        north, west = bounds[0]
        south, east = bounds[1]
        
        if south <= lat <= north and west <= lon <= east:
            return province
    
    # Jika tidak ditemukan, coba dengan toleransi yang lebih besar
    for province, data in INDONESIA_PROVINCES.items():
        bounds = data['bounds']
        north, west = bounds[0]
        south, east = bounds[1]
        
        # Tambah toleransi 0.5 derajat
        if (south - 0.5) <= lat <= (north + 0.5) and (west - 0.5) <= lon <= (east + 0.5):
            return province
    
    return 'LAINNYA'

def create_enhanced_outlet_popup(outlet, province, detailed_facilities=None, indomaret_count=0):
    """
    Popup outlet dengan modern UI design dan informasi Indomaret
    """
    # Hitung jumlah fasilitas di sekitar - warna yang benar-benar berbeda
    categories = [
        ('Residential', 'residential', 'home', '#228B22'),        # Forest Green
        ('Education', 'education', 'graduation-cap', '#4169E1'),  # Royal Blue  
        ('Public Area', 'public_area', 'tree', '#FF00FF'),       # Magenta
        ('Culinary', 'culinary', 'utensils', '#FFA500'),         # Orange
        ('Business Center', 'business_center', 'briefcase', '#40e0d0'), # Dark Slate Gray
        ('Groceries', 'groceries', 'shopping-cart', '#008080'),  # Teal
        ('Convenient Stores', 'convenient_stores', 'shopping-basket', '#FFD700'), # Gold
        ('Industrial', 'industrial', 'industry', '#4B0082'),     # Indigo
        ('Hospital/Clinic', 'hospital_clinic', 'plus', '#DC143C') # Crimson
    ]
    
    facilities_count = sum([outlet.get(cat[0], False) for cat in categories])
    
    # Tentukan rating berdasarkan jumlah fasilitas dengan warna yang sangat berbeda
    if facilities_count >= 7:
        rating = "⭐⭐⭐⭐⭐ Excellent"
        rating_color = "#006400"  # Dark Green
    elif facilities_count >= 5:
        rating = "⭐⭐⭐⭐ Very Good"
        rating_color = "#0066FF"  # Bright Blue
    elif facilities_count >= 3:
        rating = "⭐⭐⭐ Good"
        rating_color = "#800080"  # Purple
    elif facilities_count >= 1:
        rating = "⭐⭐ Fair"
        rating_color = "#FF4500"  # Orange Red
    else:
        rating = "⭐ Poor"
        rating_color = "#8B0000"  # Dark Red
    
    # Buat link ke Google Maps
    gmaps_url = f"https://www.google.com/maps?q={outlet['Latitude']},{outlet['Longitude']}"
    
    # Hitung total fasilitas detail jika tersedia
    total_detailed_facilities = 0
    if detailed_facilities:
        total_detailed_facilities = sum(len(places) for places in detailed_facilities.values())

    
    # Buat popup HTML dengan modern design
    popup_html = f"""
    <div style="min-width: 380px; max-width: 450px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
        <div style="background: #2c3e50; color: white; padding: 18px; margin: -9px -9px 15px -9px; border-radius: 8px 8px 0 0;">
            <h3 style="margin: 0; font-size: 18px; font-weight: 600;">{outlet['Nama Outlet']}</h3>
            <div style="margin-top: 8px; font-size: 14px; opacity: 0.9; display: flex; align-items: center; gap: 6px;">
                <i class="fa fa-map-marker" style="color: #3498db;"></i>
                <span>{province}</span>
            </div>
        </div>
        
        
        <div style="margin-bottom: 15px;">
            <div style="background-color: {rating_color}; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: 600;">
                {rating} ({facilities_count}/9 fasilitas)
            </div>
        </div>
        
        <div style="margin-bottom: 15px; padding: 12px; background: #ecf0f1; border-radius: 6px;">
            <div style="font-size: 13px; color: #2c3e50;">
                <strong> Koordinat:</strong> {outlet['Koordinat']}
            </div>
        </div>
        
        <div style="margin-bottom: 15px;">
            <h4 style="margin: 0 0 12px 0; color: #2c3e50; font-size: 15px; font-weight: 600;">
                Fasilitas Sekitar (100m):
            </h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">
    """
    
    # Tambahkan daftar fasilitas dengan modern design
    for category_name, category_key, icon, color in categories:
        status = outlet.get(category_name, False)
        status_icon = "✅" if status else "❌"
        opacity = "1.0" if status else "0.4"
        bg_color = "#d5f4e6" if status else "#f8f9fa"
        
        # Hitung jumlah lokasi detail untuk kategori ini
        detail_count = ""
        if status and detailed_facilities and category_name in detailed_facilities:
            count = len(detailed_facilities[category_name])
            detail_count = f" ({count})" if count > 0 else ""
        
        popup_html += f"""
            <div style="display: flex; align-items: center; padding: 8px; opacity: {opacity}; 
                        background: {bg_color}; border-radius: 4px; margin-bottom: 2px;">
                <i class="fa fa-{icon}" style="color: {color}; margin-right: 8px; width: 16px;"></i>
                <span style="font-size: 12px; flex: 1; color: #2c3e50;">{category_name}{detail_count}</span>
                <span style="margin-left: auto;">{status_icon}</span>
            </div>
        """
    
    # Tambahkan informasi total fasilitas detail jika ada
    detail_info = ""
    if total_detailed_facilities > 0:
        detail_info = f"""
        <div style="background: #d4edda; padding: 12px; border-radius: 6px; margin-bottom: 15px; text-align: center; border-left: 4px solid #006400;">
            <strong style="color: #155724;"> {total_detailed_facilities} lokasi fasilitas ditemukan</strong>
            <div style="font-size: 11px; color: #155724; margin-top: 4px;">Lihat marker berwarna di sekitar outlet ini</div>
        </div>
        """
    
    popup_html += f"""
            </div>
        </div>
        
        {detail_info}
        
        <div style="margin-top: 15px;">
            <a href="{gmaps_url}" target="_blank" 
               style="display: block; padding: 12px; background: #4169E1; color: white; text-decoration: none; 
               border-radius: 6px; text-align: center; font-weight: 600; transition: background 0.3s;">
                <i class="fa fa-external-link" style="margin-right: 8px;"></i>Buka di Google Maps
            </a>
        </div>
        
        <div style="margin-top: 12px; text-align: center; font-size: 11px; color: #7f8c8d; 
                    padding: 8px; background: #f8f9fa; border-radius: 4px;">
             Data analisis dalam radius 100 meter
        </div>
    </div>
    """
    
    return popup_html

def add_facility_markers_to_map(folium_map, outlet, detailed_facilities):
    """
    Menambahkan marker fasilitas sekitar ke peta
    """
    from api_handler import get_facility_marker_config, create_facility_popup
    
    marker_config = get_facility_marker_config()
    total_markers = 0
    
    for category, places in detailed_facilities.items():
        if not places:
            continue
            
        config = marker_config.get(category, {})
        
        for place in places:
            if not place.get('lat') or not place.get('lon'):
                continue
                
            try:
                # Buat popup untuk fasilitas
                popup_html = create_facility_popup(place, category)
                
                # Tentukan icon dan warna dengan mapping yang sangat berbeda
                icon_name = config.get('icon', 'map-marker')
                icon_color = config.get('color', '#666666')
                
                # Konversi hex color ke nama warna Folium dengan warna yang sangat kontras
                color_map = {
                    '#228B22': 'green',       # Residential - Forest Green
                    '#4169E1': 'blue',        # Education - Royal Blue
                    '#FF00FF': 'purple',      # Public Area - Magenta
                    '#FFA500': 'orange',      # Culinary - Orange
                    '#2F4F4F': 'darkblue',    # Business Center - Dark Slate Gray
                    '#008080': 'lightgreen',  # Groceries - Teal
                    '#FFD700': 'yellow',      # Convenient Stores - Gold
                    '#4B0082': 'darkred',     # Industrial - Indigo
                    '#DC143C': 'red'          # Hospital - Crimson
                }
                folium_color = color_map.get(icon_color, 'gray')
                
                # Tambahkan marker fasilitas
                folium.Marker(
                    location=[place['lat'], place['lon']],
                    popup=folium.Popup(popup_html, max_width=350),
                    tooltip=f"{place.get('name', 'Unnamed')} ({category})",
                    icon=folium.Icon(
                        color=folium_color,
                        icon=icon_name if icon_name in ['home', 'star', 'plus'] else 'info-sign',
                        prefix='glyphicon'
                    )
                ).add_to(folium_map)
                
                total_markers += 1
                
            except Exception as e:
                logger.warning(f"Error adding facility marker for {place.get('name', 'Unknown')}: {e}")
                continue
    
    return total_markers

def create_base_map(center, zoom, province_name=None):
    """
    Membuat base map dengan konfigurasi yang sesuai
    
    Parameters:
    center (list): Koordinat center [lat, lon]
    zoom (int): Zoom level
    province_name (str): Nama provinsi untuk title
    
    Returns:
    folium.Map: Base map object
    """
    map_title = f"Peta Outlet - {province_name}" if province_name else "Peta Outlet - Semua Provinsi"
    
    # Buat peta
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles='OpenStreetMap',
        attr='Map data © OpenStreetMap contributors'
    )
    
    # Tambahkan tile layers
    folium.TileLayer(
        tiles='https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        attr='Map data: © OpenStreetMap contributors, SRTM | Map style: © OpenTopoMap (CC-BY-SA)',
        name=' Topographic',
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        name=' Satellite',
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        attr='© OpenStreetMap contributors © CARTO',
        name=' Dark Mode',
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        attr='© OpenStreetMap contributors © CARTO',
        name='Light Mode',
        control=True
    ).add_to(m)
    
    return m

def create_map_legend_with_indomaret(enable_clustering=True):
    """
    Membuat legend untuk map termasuk informasi Indomaret dan clustering
    
    Parameters:
    enable_clustering (bool): Whether clustering is enabled
    
    Returns:
    str: HTML legend
    """
    
    legend_html = f"""
    <div id="map-legend" class="side-panel right-panel">
        <div class="toggle-button" onclick="togglePanel('map-legend')">
            <i class="fas fa-chevron-left"></i>
        </div>
        <div class="panel-content">
            <h4 style="margin: 0 0 15px 0; font-size: 16px; font-weight: 600; color: #4169E1; 
                       border-bottom: 2px solid #34495e; padding-bottom: 8px;">
                Rating & Kategori
            </h4>
            
            
            <div style="margin-bottom: 15px;">
                <h5 style="margin: 0 0 10px 0; color: #FFA500; font-size: 14px;">Rating Outlet:</h5>
                <div style="font-size: 12px; line-height: 1.8;">
                    <div style="display: flex; align-items: center; margin-bottom: 5px; padding: 4px 8px; background: #34495e; border-radius: 4px;">
                        <div style="width: 12px; height: 12px; background: #006400; border-radius: 2px; margin-right: 8px;"></div>
                        <span>Excellent (7-9 fasilitas)</span>
                    </div>
                    <div style="display: flex; align-items: center; margin-bottom: 5px; padding: 4px 8px; background: #34495e; border-radius: 4px;">
                        <div style="width: 12px; height: 12px; background: #0066FF; border-radius: 2px; margin-right: 8px;"></div>
                        <span>Very Good (5-6 fasilitas)</span>
                    </div>
                    <div style="display: flex; align-items: center; margin-bottom: 5px; padding: 4px 8px; background: #34495e; border-radius: 4px;">
                        <div style="width: 12px; height: 12px; background: #800080; border-radius: 2px; margin-right: 8px;"></div>
                        <span>Good (3-4 fasilitas)</span>
                    </div>
                    <div style="display: flex; align-items: center; margin-bottom: 5px; padding: 4px 8px; background: #34495e; border-radius: 4px;">
                        <div style="width: 12px; height: 12px; background: #FF4500; border-radius: 2px; margin-right: 8px;"></div>
                        <span>Fair (1-2 fasilitas)</span>
                    </div>
                    <div style="display: flex; align-items: center; padding: 4px 8px; background: #34495e; border-radius: 4px;">
                        <div style="width: 12px; height: 12px; background: #8B0000; border-radius: 2px; margin-right: 8px;"></div>
                        <span>Poor (0 fasilitas)</span>
                    </div>
                </div>
            </div>
            
            <div style="margin-bottom: 15px;">
                <h5 style="margin: 0 0 10px 0; color: #FFA500; font-size: 14px;">Marker Types:</h5>
                <div style="font-size: 11px; line-height: 1.6;">
                    <div style="padding: 3px 6px; background: #34495e; border-radius: 3px; margin-bottom: 3px;">
                         <span style="color: #4169E1;">Outlet Utama</span>
                    </div>
                    <div style="padding: 3px 6px; background: #34495e; border-radius: 3px; margin-bottom: 3px;">
                        <span style="color: #008080;">Indomaret</span>
                    </div>
                    <div style="padding: 3px 6px; background: #34495e; border-radius: 3px;">
                         <span style="color: #FFA500;">Fasilitas Sekitar</span>
                    </div>
                </div>
            </div>
            
            <div>
                <h5 style="margin: 0 0 10px 0; color: #FFA500; font-size: 14px;">Kategori Fasilitas:</h5>
                <div style="font-size: 11px; line-height: 1.6; display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
                    <div style="padding: 3px 6px; background: #34495e; border-radius: 3px; color: #fff;">Residential</div>
                    <div style="padding: 3px 6px; background: #34495e; border-radius: 3px; color: #fff;">Education</div>
                    <div style="padding: 3px 6px; background: #34495e; border-radius: 3px; color: #fff;">Public</div>
                    <div style="padding: 3px 6px; background: #34495e; border-radius: 3px; color: #fff;">Culinary</div>
                    <div style="padding: 3px 6px; background: #34495e; border-radius: 3px; color: #fff;">Business</div>
                    <div style="padding: 3px 6px; background: #34495e; border-radius: 3px; color: #fff;">Groceries</div>
                    <div style="padding: 3px 6px; background: #34495e; border-radius: 3px; color: #fff;">Convenience</div>
                    <div style="padding: 3px 6px; background: #34495e; border-radius: 3px; color: #fff;">Industrial</div>
                    <div style="padding: 3px 6px; background: #34495e; border-radius: 3px; color: #fff;">Health</div>
                </div>
            </div>
        </div>
    </div>
    """
    
    return legend_html

def create_province_info_panel_with_indomaret(province, outlets_count, facilities_count, indomaret_count):
    """
    Membuat info panel khusus untuk provinsi dengan informasi Indomaret
    
    Parameters:
    province (str): Nama provinsi
    outlets_count (int): Jumlah outlet di provinsi
    facilities_count (int): Jumlah fasilitas di provinsi
    indomaret_count (int): Jumlah Indomaret di provinsi
    
    Returns:
    str: HTML info panel
    """
    from multi_province_utils import get_province_emoji
    from config import NAVIGATION_STYLE
    
    province_config = PROVINCE_BOUNDS.get(province)
    emoji = get_province_emoji(province)
    
    # Tentukan level kompetisi dengan warna yang sangat berbeda
    if indomaret_count == 0:
        competition_status = "Peluang Bagus"
        competition_color = "#008000"  # Green
        competition_desc = "Tidak ada kompetitor Indomaret"
    elif indomaret_count <= 3:
        competition_status = "Kompetisi Rendah"
        competition_color = "#FF8C00"  # Dark Orange
        competition_desc = f"{indomaret_count} Indomaret terdeteksi"
    elif indomaret_count <= 10:
        competition_status = "Kompetisi Sedang"
        competition_color = "#9932CC"  # Dark Orchid
        competition_desc = f"{indomaret_count} Indomaret terdeteksi"
    else:
        competition_status = "Kompetisi Tinggi"
        competition_color = "#FF0000"  # Red
        competition_desc = f"{indomaret_count} Indomaret terdeteksi"
    
    info_panel = f"""
    <div id="province-info" class="side-panel left-panel">
        <div class="toggle-button" onclick="togglePanel('province-info')">
            <i class="fas fa-chevron-right"></i>
        </div>
        <div class="panel-content">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 15px;">
                <div style="background: #4169E1; padding: 8px; border-radius: 6px; font-size: 20px;">
                    {emoji}
                </div>
                <div>
                    <h3 style="margin: 0; font-size: 18px; font-weight: 600;">{province}</h3>
                    <div style="font-size: 12px; color: #bdc3c7; margin-top: 2px;">Provinsi Focus Map</div>
                </div>
            </div>
            
            <div style="background: #34495e; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #FFA500;">Data Provinsi:</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 12px;">
                    <div style="text-align: center; padding: 8px; background: #2c3e50; border-radius: 4px;">
                        <div style="font-weight: bold; color: #4169E1;">{outlets_count}</div>
                        <div style="color: #bdc3c7;">Outlets</div>
                    </div>
                    <div style="text-align: center; padding: 8px; background: #2c3e50; border-radius: 4px;">
                        <div style="font-weight: bold; color: #FFA500;">{facilities_count}</div>
                        <div style="color: #bdc3c7;">Fasilitas</div>
                    </div>
                    <div style="text-align: center; padding: 8px; background: #2c3e50; border-radius: 4px;">
                        <div style="font-weight: bold; color: #008080;">{indomaret_count}</div>
                        <div style="color: #bdc3c7;">Indomaret</div>
                    </div>
                </div>
            </div>
            
            <div style="background: {competition_color}; color: white; padding: 12px; border-radius: 8px; text-align: center;">
                <div style="font-weight: bold; font-size: 14px; margin-bottom: 4px;">
                    {competition_status}
                </div>
                <div style="font-size: 11px; opacity: 0.9;">
                    {competition_desc}
                </div>
            </div>
        </div>
    </div>
    """
    
    return info_panel

def create_full_map_info_panel(total_outlets, total_facilities, total_indomaret, outlets_by_province):
    """
    Creates a collapsible info panel for the full map view
    
    Parameters:
    total_outlets (int): Total outlet count
    total_facilities (int): Total facilities count
    total_indomaret (int): Total indomaret count
    outlets_by_province (dict): Outlets grouped by province
    
    Returns:
    str: HTML info panel
    """
    # Make sure there's actual code here, not just a docstring
    provinces_with_indomaret = len([p for p, o in outlets_by_province.items() if any(outlet.get('Indomaret_Count', 0) > 0 for outlet in o)])
    
    info_panel = f"""
    <div id="full-map-info" class="side-panel left-panel">
        <div class="toggle-button" onclick="togglePanel('full-map-info')">
            <i class="fas fa-chevron-right"></i>
        </div>
        <div class="panel-content">
            <div style="background: #34495e; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #FFA500;"> Total Data:</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px;">
                    <div style="text-align: center; padding: 8px; background: #2c3e50; border-radius: 4px;">
                        <div style="font-weight: bold; color: #4169E1;">{total_outlets}</div>
                        <div style="color: #bdc3c7;">Total Outlets</div>
                    </div>
                    <div style="text-align: center; padding: 8px; background: #2c3e50; border-radius: 4px;">
                        <div style="font-weight: bold; color: #FFA500;">{total_facilities}</div>
                        <div style="color: #bdc3c7;">Total Fasilitas</div>
                    </div>
                </div>
                <div style="margin-top: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px;">
                    <div style="text-align: center; padding: 8px; background: #2c3e50; border-radius: 4px;">
                        <div style="font-weight: bold; color: #008080;">{total_indomaret}</div>
                        <div style="color: #bdc3c7;">Total Indomaret</div>
                    </div>
                    <div style="text-align: center; padding: 8px; background: #2c3e50; border-radius: 4px;">
                        <div style="font-weight: bold; color: #FF8C00;">{len(outlets_by_province)}</div>
                        <div style="color: #bdc3c7; font-size: 11px;">Provinsi Tersedia</div>
                    </div>
                </div>
            </div>
            
            <div style="background: #FF6002; color: white; padding: 12px; border-radius: 8px; text-align: center;">
                <div style="font-weight: bold; font-size: 14px; margin-bottom: 4px;">
                     Analisis Kompetisi
                </div>
                <div style="font-size: 11px; opacity: 0.9;">
                    Indomaret tersebar di {provinces_with_indomaret} provinsi
                </div>
            </div>
        </div>
    </div>
    """
    
    return info_panel
def create_collapsible_toolbar(excel_file=None, timestamp=None):
    """
    Create a collapsible toolbar with download links
    
    Parameters:
    excel_file (str): Path to Excel file for download
    timestamp (str): Timestamp for display
    
    Returns:
    str: HTML for the collapsible toolbar
    """
    if not timestamp:
        from datetime import datetime
        timestamp = datetime.now().strftime('%d-%m-%Y %H:%M')
    
    toolbar_html = """
    <div id="map-toolbar" class="side-panel top-panel">
        <div class="toggle-button" onclick="togglePanel('map-toolbar')">
            <i class="fas fa-chevron-up"></i>
        </div>
        <div class="panel-content">
            <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap; justify-content: center;">
    """
    
    # Add Excel download button if file exists
    if excel_file and os.path.exists(excel_file):
        excel_filename = os.path.basename(excel_file)
        excel_rel_path = excel_filename
        
        toolbar_html += f"""
                <a href="{excel_rel_path}" download="{excel_filename}" 
                   style="display: flex; align-items: center; gap: 8px; padding: 10px 16px; 
                   background: #FF6002; color: white; text-decoration: none; 
                   border-radius: 6px; font-weight: 600; transition: background 0.3s ease;">
                   <i class="fas fa-download"></i>
                   <span>Download Excel</span>
                </a>
        """
    
    # Add Dashboard button
    toolbar_html += """
                <a href="/dashboard" 
                   style="display: flex; align-items: center; gap: 8px; padding: 10px 16px; 
                   background: #FF6002; color: white; text-decoration: none; 
                   border-radius: 6px; font-weight: 600; transition: background 0.3s ease;">
                  <i class="fas fa-chart-line"></i>
                   <span>Dashboard</span>
                </a>
            </div>
            
            <div style="text-align: center; margin-top: 12px; font-size: 12px; color: #bdc3c7;">
                <i class="fas fa-clock"></i> Update: {timestamp} WIB
            </div>
        </div>
    </div>
    """
    
    return toolbar_html

def add_panel_styles(folium_map):
    """
    Adds common CSS styles for panels to a map
    
    Parameters:
    folium_map: Folium map object to add styles to
    """
    panel_css = """
    <style>
    /* Common panel styles */
    .side-panel {
        position: fixed;
        z-index: 1000;
        background: #2c3e50;
        color: #ecf0f1;
        padding: 18px;
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        border: 1px solid #34495e;
        transition: transform 0.3s ease;
        max-width: 370px;
    }
    
    /* Panel positions */
    .right-panel {
        right: 20px;
        bottom: 200px;
    }
    
    .left-panel {
        left: 20px;
        bottom: 100px;
    }
    
    .top-panel {
        top: 20px;
        right: 20px;
    }
    
    /* Toggle button styles */
    .toggle-button {
        position: absolute;
        background: #2c3e50;
        color: #ecf0f1;
        width: 30px;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        border: 1px solid #34495e;
        box-shadow: 0 0 10px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    
    /* Right panel toggle */
    .right-panel .toggle-button {
        left: -30px;
        top: 50%;
        transform: translateY(-50%);
        border-radius: 10px 0 0 10px;
        border-right: none;
    }
    
    /* Left panel toggle */
    .left-panel .toggle-button {
        right: -30px;
        top: 50%;
        transform: translateY(-50%);
        border-radius: 0 10px 10px 0;
        border-left: none;
    }
    
    /* Top panel toggle */
    .top-panel .toggle-button {
        bottom: -30px;
        left: 50%;
        transform: translateX(-50%);
        width: 60px;
        height: 30px;
        border-radius: 0 0 10px 10px;
        border-top: none;
    }
    
    /* Collapsed states */
    .right-panel.collapsed {
        transform: translateX(calc(100% + 30px));
    }
    
    .left-panel.collapsed {
        transform: translateX(calc(-100% + -30px));
    }
    
    .top-panel.collapsed {
        transform: translateY(calc(-100% + -30px));
    }
    
    /* Panel content */
    .panel-content {
        overflow: hidden;
    }
    </style>
    """
    
    folium_map.get_root().html.add_child(folium.Element(panel_css))

def add_common_panel_scripts(folium_map):
    """
    Adds common JavaScript for panel functionality to a map
    
    Parameters:
    folium_map: Folium map object to add scripts to
    """
    common_js = """
    <script>
    // Function to toggle panel visibility
    function togglePanel(panelId) {
        const panel = document.getElementById(panelId);
        if (!panel) return;
        
        // Toggle collapsed class
        panel.classList.toggle('collapsed');
        
        // Save state in localStorage
        localStorage.setItem(panelId + '_collapsed', panel.classList.contains('collapsed'));
    }
    
    // Function to initialize panels on page load
    function initPanels() {
        // List of all panel IDs
        const panelIds = ['map-legend', 'province-info', 'map-toolbar', 'full-map-info'];
        
        // Initialize each panel
        panelIds.forEach(panelId => {
            const panel = document.getElementById(panelId);
            if (!panel) return;
            
            // Check stored state
            const isCollapsed = localStorage.getItem(panelId + '_collapsed') === 'true';
            
            // Apply initial state
            if (isCollapsed) {
                panel.classList.add('collapsed');
            } else {
                panel.classList.remove('collapsed');
            }
            
            // Update toggle button icon
            const toggleButton = panel.querySelector('.toggle-button i');
            if (toggleButton) {
                if (panel.classList.contains('collapsed')) {
                    if (panelId === 'map-toolbar') {
                        toggleButton.className = 'fas fa-chevron-down';
                    } else if (panelId.includes('info')) {
                        toggleButton.className = 'fas fa-chevron-left';
                    } else {
                        toggleButton.className = 'fas fa-chevron-right';
                    }
                } else {
                    if (panelId === 'map-toolbar') {
                        toggleButton.className = 'fas fa-chevron-up';
                    } else if (panelId.includes('info')) {
                        toggleButton.className = 'fas fa-chevron-right';
                    } else {
                        toggleButton.className = 'fas fa-chevron-left';
                    }
                }
            }
        });
    }
    
    // Initialize panels on page load
    document.addEventListener('DOMContentLoaded', initPanels);
    </script>
    """
    
    folium_map.get_root().html.add_child(folium.Element(common_js))

def add_map_plugins(folium_map):
    """
    Menambahkan plugins ke map
    
    Parameters:
    folium_map: Folium map object
    """
    # Tambahkan LayerControl
    folium.LayerControl(
        position='bottomright',
        collapsed=False,
        autoZIndex=True
    ).add_to(folium_map)
    
    # Tambahkan plugins
    plugins.Fullscreen(
        position='topleft',
        title='Mode Fullscreen',
        title_cancel='Keluar Fullscreen',
        force_separate_button=True
    ).add_to(folium_map)
    
    plugins.MeasureControl(
        position='bottomleft',
        primary_length_unit='meters',
        secondary_length_unit='kilometers',
        primary_area_unit='sqmeters',
        secondary_area_unit='hectares'
    ).add_to(folium_map)
    
    plugins.LocateControl(
        auto_start=False,
        position='topleft'
    ).add_to(folium_map)
    
    # Add JavaScript to handle plugin interaction with panels
    plugin_interaction_js = """
    <script>
    // Adjust panels on fullscreen toggle
    document.addEventListener('fullscreenchange', adjustPanelsOnFullscreen);
    document.addEventListener('webkitfullscreenchange', adjustPanelsOnFullscreen);
    document.addEventListener('mozfullscreenchange', adjustPanelsOnFullscreen);
    document.addEventListener('MSFullscreenChange', adjustPanelsOnFullscreen);
    
    function adjustPanelsOnFullscreen() {
        const isFullscreen = document.fullscreenElement || 
                            document.webkitFullscreenElement || 
                            document.mozFullScreenElement || 
                            document.msFullscreenElement;
        
        // List of all panels
        const panels = document.querySelectorAll('.side-panel');
        
        if (isFullscreen) {
            // In fullscreen, adjust z-index to make panels visible above map
            panels.forEach(panel => {
                panel.style.zIndex = '9999';
            });
        } else {
            // Reset z-index when exiting fullscreen
            panels.forEach(panel => {
                panel.style.zIndex = '1000';
            });
        }
    }
    </script>
    """
    
    folium_map.get_root().html.add_child(folium.Element(plugin_interaction_js))

def initialize_collapsible_panels(folium_map, excel_file=None, province_name=None, outlets_by_province=None, total_outlets=None, total_facilities=None, total_indomaret=None):
    """
    Initializes all collapsible panels for a map
    
    Parameters:
    folium_map: Folium map object
    excel_file: Path to Excel file (optional)
    province_name: Name of province for province map (optional)
    outlets_by_province: Dictionary of outlets by province (optional)
    total_outlets: Total number of outlets (optional)
    total_facilities: Total number of facilities (optional)
    total_indomaret: Total number of Indomaret stores (optional)
    """
    # Add common CSS styles
    add_panel_styles(folium_map)
    
    # Add toolbar if Excel file is available
    if excel_file and os.path.exists(excel_file):
        toolbar_html = create_collapsible_toolbar(excel_file)
        folium_map.get_root().html.add_child(folium.Element(toolbar_html))
    
    # Add legend
    legend_html = create_map_legend_with_indomaret(enable_clustering=True)
    folium_map.get_root().html.add_child(folium.Element(legend_html))
    
    # Add appropriate info panel based on map type
    if province_name:
        # For province map
        province_info = create_province_info_panel_with_indomaret(
            province_name, 
            len(outlets_by_province.get(province_name, [])), 
            sum(sum(len(outlet.get('detailed_facilities', {}).get(cat, [])) for cat in outlet.get('detailed_facilities', {})) for outlet in outlets_by_province.get(province_name, [])), 
            sum(outlet.get('Indomaret_Count', 0) for outlet in outlets_by_province.get(province_name, []))
        )
        folium_map.get_root().html.add_child(folium.Element(province_info))
    elif outlets_by_province and total_outlets:
        # For full map
        full_map_info = create_full_map_info_panel(
            total_outlets, 
            total_facilities, 
            total_indomaret, 
            outlets_by_province
        )
        folium_map.get_root().html.add_child(folium.Element(full_map_info))
    
    # Add logo
    logo_html = """
    <div style="position: fixed; top: 20px; left: 450px; z-index: 1000;">
        <img src="/logo.png" alt="Logo" style="width: 100px;border-radius: 5px;">
    </div>
    """
    folium_map.get_root().html.add_child(folium.Element(logo_html))
    
    # Add common scripts
    add_common_panel_scripts(folium_map)

def create_optimized_cluster(name, cluster_type="outlet"):
    """
    Membuat cluster yang dioptimalkan berdasarkan konfigurasi
    
    Parameters:
    name (str): Nama cluster
    cluster_type (str): Tipe cluster ("outlet", "facility", "indomaret")
    
    Returns:
    MarkerCluster: Cluster yang sudah dikonfigurasi
    """
    # Ambil pengaturan dari config
    settings = CLUSTERING_SETTINGS
    
    if cluster_type == "outlet":
        radius = settings.get('OUTLET_CLUSTER_RADIUS', 50)
        max_zoom = settings.get('MAX_ZOOM_LEVEL', 15)
    elif cluster_type == "facility":
        radius = settings.get('FACILITY_CLUSTER_RADIUS', 40)
        max_zoom = settings.get('MAX_ZOOM_LEVEL', 16)
    elif cluster_type == "indomaret":
        radius = settings.get('INDOMARET_CLUSTER_RADIUS', 60)
        max_zoom = settings.get('MAX_ZOOM_LEVEL', 14)
    else:
        radius = 50
        max_zoom = 15
    
    # Mode clustering agresif untuk dataset besar
    if settings.get('AGGRESSIVE_CLUSTERING', False):
        radius = radius * 1.5  # Tingkatkan radius
        max_zoom = max_zoom - 2  # Turunkan max zoom
    
    cluster_options = {
        'maxClusterRadius': int(radius),
        'spiderfyOnMaxZoom': settings.get('ENABLE_SPIDERFY', True),
        'showCoverageOnHover': not settings.get('DISABLE_COVERAGE_ON_HOVER', True),
        'zoomToBoundsOnClick': True,
        'maxZoom': max_zoom,
        'disableClusteringAtZoom': max_zoom + 3,  # Buka semua cluster di zoom tinggi
        'animateAddingMarkers': False,  # Nonaktifkan animasi untuk performa
        'removeOutsideVisibleBounds': True  # Hapus marker di luar viewport
    }
    
    return MarkerCluster(
        name=name,
        overlay=True,
        control=True,
        options=cluster_options
    )

def add_outlets_and_facilities_to_map(folium_map, outlets, province_name, indomaret_handler=None, enable_clustering=None):
    """
    Menambahkan outlet dan fasilitas ke map dengan integrasi Indomaret dan clustering
    
    Parameters:
    folium_map: Folium map object
    outlets (list): List outlet untuk provinsi
    province_name (str): Nama provinsi
    indomaret_handler: Instance IndomaretHandler untuk data Indomaret
    enable_clustering (bool): Enable marker clustering (None = auto from config)
    
    Returns:
    tuple: (total_outlets, total_facilities, total_indomaret)
    """
    total_outlets = len(outlets)
    total_facilities = 0
    total_indomaret = 0
    
    # Tentukan apakah clustering diaktifkan berdasarkan ukuran dataset
    if enable_clustering is None:
        enable_clustering = CLUSTERING_SETTINGS.get('ENABLE_CLUSTERING', True)
        
        # Auto disable untuk dataset kecil
        disable_threshold = CLUSTERING_SETTINGS.get('DISABLE_CLUSTERING_THRESHOLD', 50)
        if total_outlets < disable_threshold:
            enable_clustering = False
            logger.info(f"Dataset kecil ({total_outlets} outlets), clustering dinonaktifkan untuk performa optimal")
    
    # Create clustering groups
    outlet_clusters = {}
    facility_cluster = None
    indomaret_cluster = None
    
    if enable_clustering:
        # Deteksi dataset besar dan aktifkan mode agresif jika perlu
        aggressive_threshold = CLUSTERING_SETTINGS.get('AUTO_AGGRESSIVE_THRESHOLD', 1000)
        original_setting = None
        
        if total_outlets > aggressive_threshold:
            logger.info(f"Dataset besar terdeteksi ({total_outlets} outlets), mengaktifkan clustering agresif")
            original_setting = CLUSTERING_SETTINGS.get('AGGRESSIVE_CLUSTERING', False)
            CLUSTERING_SETTINGS['AGGRESSIVE_CLUSTERING'] = True
        
        # Create separate clusters using optimized function
        outlet_clusters = {
            'excellent': create_optimized_cluster("⭐ Excellent Outlets", "outlet"),
            'very_good': create_optimized_cluster("🔵 Very Good Outlets", "outlet"), 
            'good': create_optimized_cluster("🟢 Good Outlets", "outlet"),
            'fair': create_optimized_cluster("🟡 Fair Outlets", "outlet"),
            'poor': create_optimized_cluster("🔴 Poor Outlets", "outlet")
        }
        
        # Create clusters for facilities and indomaret
        facility_cluster = create_optimized_cluster("🏢 Fasilitas Sekitar", "facility")
        indomaret_cluster = create_optimized_cluster("🏪 Indomaret", "indomaret")
        
        # Reset setting jika diubah otomatis
        if original_setting is not None:
            CLUSTERING_SETTINGS['AGGRESSIVE_CLUSTERING'] = original_setting
        
        # Add clusters to map
        for cluster in outlet_clusters.values():
            cluster.add_to(folium_map)
        facility_cluster.add_to(folium_map)
        indomaret_cluster.add_to(folium_map)
    
    for outlet in outlets:
        # Hitung jumlah fasilitas
        facilities_count = sum([
            outlet.get('Residential', False),
            outlet.get('Education', False),
            outlet.get('Public Area', False),
            outlet.get('Culinary', False),
            outlet.get('Business Center', False),
            outlet.get('Groceries', False),
            outlet.get('Convenient Stores', False),
            outlet.get('Industrial', False),
            outlet.get('Hospital/Clinic', False)
        ])
        
        # Tentukan warna dan icon marker outlet dengan warna yang sangat berbeda
        if facilities_count >= 7:
            color = 'darkgreen'   # Excellent - Dark Green
            icon = 'star'
            cluster_key = 'excellent'
        elif facilities_count >= 5:
            color = 'blue'        # Very Good - Blue  
            icon = 'thumbs-up'
            cluster_key = 'very_good'
        elif facilities_count >= 3:
            color = 'purple'      # Good - Purple
            icon = 'ok-sign'
            cluster_key = 'good'
        elif facilities_count >= 1:
            color = 'orange'      # Fair - Orange
            icon = 'minus-sign'
            cluster_key = 'fair'
        else:
            color = 'red'         # Poor - Red
            icon = 'remove-sign'
            cluster_key = 'poor'
        
        # Ambil informasi Indomaret untuk outlet ini
        indomaret_count = outlet.get('Indomaret_Count', 0)
        
        # Buat popup enhanced untuk outlet dengan info Indomaret
        detailed_facilities = outlet.get('detailed_facilities', {})
        popup_html = create_enhanced_outlet_popup(outlet, province_name, detailed_facilities, indomaret_count)
        
        # Buat marker outlet
        outlet_marker = folium.Marker(
            location=[outlet['Latitude'], outlet['Longitude']],
            popup=folium.Popup(popup_html, max_width=450),
            tooltip=f"🏢 {outlet['Nama Outlet']} ({province_name}) - {facilities_count}/9 fasilitas, {indomaret_count} Indomaret",
            icon=folium.Icon(
                color=color,
                icon=icon,
                prefix='glyphicon'
            )
        )
        
        # Tambahkan marker ke cluster atau langsung ke map
        if enable_clustering and cluster_key in outlet_clusters:
            outlet_marker.add_to(outlet_clusters[cluster_key])
        else:
            outlet_marker.add_to(folium_map)
        
        # Tambahkan marker fasilitas sekitar jika ada
        if detailed_facilities:
            if enable_clustering and facility_cluster:
                facility_count = add_facility_markers_to_map(facility_cluster, outlet, detailed_facilities)
            else:
                facility_count = add_facility_markers_to_map(folium_map, outlet, detailed_facilities)
            total_facilities += facility_count
        
        # Tambahkan marker Indomaret jika ada handler dan koordinat outlet tersedia
        if indomaret_handler and outlet.get('Latitude') and outlet.get('Longitude'):
            if enable_clustering and indomaret_cluster:
                indomaret_added = indomaret_handler.add_indomaret_markers_to_map(
                    indomaret_cluster, outlet['Latitude'], outlet['Longitude'], radius_km=0.5
                )
            else:
                indomaret_added = indomaret_handler.add_indomaret_markers_to_map(
                    folium_map, outlet['Latitude'], outlet['Longitude'], radius_km=0.5
                )
            total_indomaret += indomaret_added
    
    return total_outlets, total_facilities, total_indomaret

def create_province_map(province_name, outlets, output_file, excel_file=None, indomaret_handler=None, enable_clustering=True):
    """
    Membuat map khusus untuk satu provinsi dengan integrasi Indomaret dan clustering
    
    Parameters:
    province_name (str): Nama provinsi
    outlets (list): List outlet untuk provinsi ini
    output_file (str): Nama file output
    excel_file (str): Path ke file Excel (optional)
    indomaret_handler: Instance IndomaretHandler (optional)
    enable_clustering (bool): Enable marker clustering (default: True)
    
    Returns:
    str: Path ke file output atau None jika gagal
    """
    try:
        province_config = PROVINCE_BOUNDS.get(province_name)
        if not province_config:
            logger.error(f"Konfigurasi tidak ditemukan untuk provinsi: {province_name}")
            return None
        
        logger.info(f"Creating map for {province_name} with {len(outlets)} outlets...")
        
        # Buat base map dengan center dan zoom khusus provinsi
        m = create_base_map(
            center=province_config['center'],
            zoom=province_config['zoom'],
            province_name=province_name
        )
        
        # Group outlets by province for panel initialization
        outlets_by_province = {province_name: outlets}
        
        # Tambahkan outlets dan fasilitas dengan integrasi Indomaret dan clustering
        total_outlets, total_facilities, total_indomaret = add_outlets_and_facilities_to_map(
            m, outlets, province_name, indomaret_handler, enable_clustering
        )
        
        # Tambahkan plugins
        add_map_plugins(m)
        
        # Tambahkan navigation
        navigation_html = create_province_navigation(current_province=province_name)
        m.get_root().html.add_child(folium.Element(navigation_html))
        
        # Initialize all collapsible panels
        initialize_collapsible_panels(
            m,
            excel_file=excel_file,
            province_name=province_name,
            outlets_by_province=outlets_by_province
        )
        
        # Simpan map ke file
        m.save(output_file)
        
        logger.info(f"Province map created successfully: {output_file}")
        logger.info(f"  Province: {province_name}")
        logger.info(f"  Outlets: {total_outlets}")
        logger.info(f"  Facilities: {total_facilities}")
        logger.info(f"  Indomaret: {total_indomaret}")
        logger.info(f"  Center: {province_config['center']}")
        logger.info(f"  Zoom: {province_config['zoom']}")
        
        return os.path.abspath(output_file)
        
    except Exception as e:
        logger.error(f"Error creating province map for {province_name}: {e}")
        return None

def create_full_map(results, output_file, excel_file=None, indomaret_handler=None, enable_clustering=True):
    """
    Membuat map dengan semua provinsi dengan integrasi Indomaret dan clustering
    
    Parameters:
    results (list): Semua hasil analisis outlet
    output_file (str): Nama file output
    excel_file (str): Path ke file Excel (optional)
    indomaret_handler: Instance IndomaretHandler (optional)
    enable_clustering (bool): Enable marker clustering (default: True)
    
    Returns:
    str: Path ke file output atau None jika gagal
    """
    try:
        logger.info(f"Creating full map with all {len(results)} outlets...")
        
        # Kelompokkan outlet berdasarkan provinsi
        outlets_by_province = group_outlets_by_province(results)
        
        # Buat base map dengan center di Indonesia tengah
        m = create_base_map(
            center=[-2.5, 118.0],
            zoom=5,
            province_name=None
        )
        
        total_outlets = 0
        total_facilities = 0
        total_indomaret = 0
        
        # Tambahkan outlet dari semua provinsi dengan clustering
        for province, outlets in outlets_by_province.items():
            if province in PROVINCE_BOUNDS:  # Hanya provinsi yang dikonfigurasi
                province_outlets, province_facilities, province_indomaret = add_outlets_and_facilities_to_map(
                    m, outlets, province, indomaret_handler, enable_clustering
                )
                total_outlets += province_outlets
                total_facilities += province_facilities
                total_indomaret += province_indomaret
        
        # Tambahkan plugins
        add_map_plugins(m)
        
        # Tambahkan navigation (current = None untuk full map)
        navigation_html = create_province_navigation(current_province=None)
        m.get_root().html.add_child(folium.Element(navigation_html))
        
        # Initialize all collapsible panels
        initialize_collapsible_panels(
            m,
            excel_file=excel_file,
            outlets_by_province=outlets_by_province,
            total_outlets=total_outlets,
            total_facilities=total_facilities,
            total_indomaret=total_indomaret
        )
        
        # Simpan map ke file
        m.save(output_file)
        
        logger.info(f"Full map created successfully: {output_file}")
        logger.info(f"  Total outlets: {total_outlets}")
        logger.info(f"  Total facilities: {total_facilities}")
        logger.info(f"  Total Indomaret: {total_indomaret}")
        logger.info(f"  Provinces: {len(outlets_by_province)}")
        
        return os.path.abspath(output_file)
        
    except Exception as e:
        logger.error(f"Error creating full map: {e}")
        return None

def generate_multi_province_maps(results, output_dir="output", excel_file=None, indomaret_json_path=None):
    """
    Membuat multiple maps: satu full map + satu map per provinsi dengan integrasi Indomaret
    
    Parameters:
    results (list): Hasil analisis outlet
    output_dir (str): Direktori output
    excel_file (str): Path ke file Excel (optional)
    indomaret_json_path (str): Path ke file JSON data Indomaret (optional)
    
    Returns:
    dict: Dictionary berisi path ke semua file yang dibuat
    """
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize Indomaret handler jika ada data
        indomaret_handler = None
        if indomaret_json_path and os.path.exists(indomaret_json_path):
            logger.info(f"Loading Indomaret data from {indomaret_json_path}")
            indomaret_handler = IndomaretHandler(indomaret_json_path)
            
            if indomaret_handler.indomaret_data:
                logger.info(f"Indomaret handler initialized with {len(indomaret_handler.indomaret_data)} stores")
                
                # Enhance outlet data dengan informasi Indomaret
                results = indomaret_handler.enhance_outlet_data_with_indomaret(results)
                logger.info("Outlet data enhanced with Indomaret information")
            else:
                logger.warning("Failed to load Indomaret data")
                indomaret_handler = None
        elif indomaret_json_path:
            logger.warning(f"Indomaret data file not found: {indomaret_json_path}")
        else:
            # Coba cari file dengan nama default
            default_paths = ["indomaret_data.json", "data_indomaret.json", "indomaret.json"]
            for path in default_paths:
                if os.path.exists(path):
                    logger.info(f"Found Indomaret data at {path}")
                    indomaret_handler = IndomaretHandler(path)
                    if indomaret_handler.indomaret_data:
                        results = indomaret_handler.enhance_outlet_data_with_indomaret(results)
                        logger.info("Outlet data enhanced with Indomaret information")
                        break
        
        # Process outlets untuk detailed facilities jika belum ada
        if results and 'detailed_facilities' not in results[0]:
            logger.info("Processing outlets for detailed facilities...")
            from api_handler import process_outlets_with_detailed_facilities
            results = process_outlets_with_detailed_facilities(results)
        
        # Kelompokkan outlet berdasarkan provinsi
        outlets_by_province = group_outlets_by_province(results)
        
        # Validasi data
        validation = validate_province_data(outlets_by_province)
        logger.info(f"Validation result: {validation['summary']}")
        
        generated_files = {}
        
        # 1. Buat full map (semua provinsi) dengan Indomaret
        full_map_file = os.path.join(output_dir, "peta_outlet_full.html")
        logger.info("Creating full map with Indomaret integration...")
        full_map_path = create_full_map(results, full_map_file, excel_file, indomaret_handler, enable_clustering=True)
        if full_map_path:
            generated_files['full'] = full_map_path
            logger.info(f"✅ Full map created: {full_map_path}")
        else:
            logger.error("❌ Failed to create full map")
        
        # 2. Buat map per provinsi dengan Indomaret
        logger.info("Creating province-specific maps with Indomaret integration...")
        generated_files['provinces'] = {}
        
        for province, outlets in outlets_by_province.items():
            if province in PROVINCE_BOUNDS:
                province_filename = get_province_map_filename(province)
                province_file_path = os.path.join(output_dir, province_filename)
                
                logger.info(f"Creating map for {province} with Indomaret data...")
                province_map_path = create_province_map(
                    province_name=province,
                    outlets=outlets,
                    output_file=province_file_path,
                    excel_file=excel_file,
                    indomaret_handler=indomaret_handler,
                    enable_clustering=True
                )
                
                if province_map_path:
                    generated_files['provinces'][province] = province_map_path
                    logger.info(f"✅ {province} map created: {province_map_path}")
                else:
                    logger.error(f"❌ Failed to create map for {province}")
            else:
                logger.warning(f"⚠️ Province {province} not configured, skipping map generation")
        
        # 3. Simpan metadata dengan info Indomaret
        save_province_map_metadata(output_dir, outlets_by_province)
        
        # 4. Generate Indomaret report jika handler tersedia
        if indomaret_handler:
            logger.info("Generating Indomaret competition report...")
            indomaret_report = indomaret_handler.generate_indomaret_report(results)
            
            # Simpan laporan Indomaret
            indomaret_report_file = os.path.join(output_dir, "indomaret_competition_report.json")
            try:
                with open(indomaret_report_file, 'w', encoding='utf-8') as f:
                    json.dump(indomaret_report, f, indent=2, ensure_ascii=False)
                logger.info(f"Indomaret report saved: {indomaret_report_file}")
                generated_files['indomaret_report'] = indomaret_report_file
            except Exception as e:
                logger.error(f"Failed to save Indomaret report: {e}")
        
        # 5. Buat index file untuk navigasi dengan info Indomaret
        create_maps_index_file_with_indomaret(output_dir, generated_files, outlets_by_province, indomaret_handler)
        
        # Summary
        total_files = len(generated_files.get('provinces', {}))
        if generated_files.get('full'):
            total_files += 1
            
        logger.info("=" * 50)
        logger.info(" MULTI-PROVINCE MAPS WITH INDOMARET INTEGRATION COMPLETE")
        logger.info("=" * 50)
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Total files created: {total_files}")
        logger.info(f"Full map: {'✅' if generated_files.get('full') else '❌'}")
        logger.info(f"Province maps: {len(generated_files.get('provinces', {}))}")
        logger.info(f" Indomaret integration: {'✅' if indomaret_handler else '❌'}")
        
        if indomaret_handler:
            stats = indomaret_handler.get_indomaret_statistics()
            logger.info(f"📊 Indomaret stores: {stats['total_stores']}")
            logger.info(f"📍 Kecamatan with Indomaret: {stats['total_kecamatan']}")
        
        for province, path in generated_files.get('provinces', {}).items():
            logger.info(f"   • {province}: {os.path.basename(path)}")
        
        return generated_files
        
    except Exception as e:
        logger.error(f"Error in generate_multi_province_maps: {e}")
        return {}

def create_maps_index_file_with_indomaret(output_dir, generated_files, outlets_by_province, indomaret_handler=None):
    """
    Membuat file index HTML untuk navigasi semua maps dengan informasi Indomaret
    
    Parameters:
    output_dir (str): Direktori output
    generated_files (dict): Dictionary file yang dibuat
    outlets_by_province (dict): Data outlet per provinsi
    indomaret_handler: Instance IndomaretHandler (optional)
    """
    try:
        index_file = os.path.join(output_dir, "maps_index.html")
        
        province_links = ""
        for province, path in generated_files.get('provinces', {}).items():
            filename = os.path.basename(path)
            outlets_count = len(outlets_by_province.get(province, []))
            
            # Hitung Indomaret di provinsi ini
            indomaret_count = 0
            if indomaret_handler:
                for outlet in outlets_by_province.get(province, []):
                    indomaret_count += outlet.get('Indomaret_Count', 0)
            
            from multi_province_utils import get_province_emoji
            emoji = get_province_emoji(province)
            
            # Tentukan status kompetisi dengan warna yang sangat berbeda
            if indomaret_count == 0:
                competition_badge = '<span style="background: #008000; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">Peluang Bagus</span>'
            elif indomaret_count <= 3:
                competition_badge = '<span style="background: #FF8C00; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">Kompetisi Rendah</span>'
            elif indomaret_count <= 10:
                competition_badge = '<span style="background: #9932CC; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">Kompetisi Sedang</span>'
            else:
                competition_badge = '<span style="background: #FF0000; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">Kompetisi Tinggi</span>'
            
            province_links += f"""
            <div class="province-card">
                <a href="{filename}" class="province-link">
                    <div class="province-header">
                        <span class="province-emoji">{emoji}</span>
                        <h3>{province}</h3>
                    </div>
                    <div class="province-stats">
                        <span class="outlet-count">{outlets_count} outlets</span>
                        <div style="margin-top: 4px;">
                            <span style="font-size: 11px; color: #666;"> {indomaret_count} Indomaret</span>
                        </div>
                        <div style="margin-top: 6px;">
                            {competition_badge}
                        </div>
                    </div>
                </a>
            </div>
            """
        
        full_map_link = ""
        if generated_files.get('full'):
            full_map_filename = os.path.basename(generated_files['full'])
            total_outlets = sum(len(outlets) for outlets in outlets_by_province.values())
            
            # Total Indomaret
            total_indomaret = 0
            if indomaret_handler:
                stats = indomaret_handler.get_indomaret_statistics()
                total_indomaret = stats['total_stores']
            
            full_map_link = f"""
            <div class="full-map-card">
                <a href="{full_map_filename}" class="full-map-link">
                    <div class="full-map-header">
                        <h2>Lihat Semua Provinsi</h2>
                    </div>
                    <div class="full-map-stats">
                        <span class="total-outlets">{total_outlets} total outlets</span>
                        <div style="margin-top: 4px;">
                            <span style="font-size: 14px; color: #008080;"> {total_indomaret} total Indomaret</span>
                        </div>
                    </div>
                </a>
            </div>
            """
        
        # Indomaret report link
        indomaret_report_link = ""
        if generated_files.get('indomaret_report'):
            indomaret_report_link = f"""
            <div style="text-align: center; margin: 20px 0;">
                <a href="{os.path.basename(generated_files['indomaret_report'])}" 
                   style="display: inline-block; padding: 12px 20px; background: #008080; color: white; 
                   text-decoration: none; border-radius: 6px; font-weight: 600;">
                    Download Laporan Kompetisi Indomaret
                </a>
            </div>
            """
        
        index_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Maps Index - Analisis Outlet dengan Indomaret</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}
        
        .maps-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .full-map-card {{
            grid-column: 1 / -1;
            margin-bottom: 20px;
        }}
        
        .province-card, .full-map-card {{
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .province-card:hover, .full-map-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.2);
        }}
        
        .province-link, .full-map-link {{
            display: block;
            text-decoration: none;
            color: inherit;
            padding: 25px;
        }}
        
        .province-header, .full-map-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }}
        
        .province-emoji, .full-map-emoji {{
            font-size: 2.5rem;
        }}
        
        .full-map-emoji {{
            font-size: 3rem;
        }}
        
        .province-header h3, .full-map-header h2 {{
            margin: 0;
            color: #2c3e50;
            font-weight: 600;
        }}
        
        .full-map-header h2 {{
            font-size: 1.8rem;
        }}
        
        .province-stats, .full-map-stats {{
            color: #7f8c8d;
            font-size: 0.9rem;
        }}
        
        .full-map-stats {{
            font-size: 1.1rem;
            font-weight: 500;
            color: #FFA500;
        }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            opacity: 0.8;
        }}
        
        @media (max-width: 768px) {{
            .maps-grid {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-map-marked-alt"></i> Maps Navigator</h1>
            <p>Pilih provinsi untuk melihat peta detail dengan analisis kompetisi Indomaret</p>
            {'<p style="font-size: 1rem; background: rgba(255,255,255,0.2); padding: 10px; border-radius: 6px; margin-top: 15px;">🏪 Termasuk data ' + str(total_indomaret if indomaret_handler else 0) + ' toko Indomaret di seluruh Indonesia</p>' if indomaret_handler else ''}
        </div>
        
        {full_map_link}
        
        <div class="maps-grid">
            {province_links}
        </div>
        
        {indomaret_report_link}
        
        <div class="footer">
            <p>&copy; {datetime.now().year} Sistem Analisis Outlet dengan Integrasi Indomaret | Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')} WIB</p>
        </div>
    </div>
</body>
</html>"""
        
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_html)
        
        logger.info(f"Maps index file with Indomaret info created: {index_file}")
        
    except Exception as e:
        logger.error(f"Error creating maps index file: {e}")

def create_dashboard(update_time, output_dir, generated_files, indomaret_stats=None):
    """
    Membuat dashboard HTML dengan peta multi-province, link download, dan info Indomaret
    
    Parameters:
    update_time (datetime): Waktu update
    output_dir (str): Direktori output
    generated_files (dict): Dictionary file yang dibuat
    indomaret_stats (dict): Statistik Indomaret (optional)
    """
    # Buat dropdown untuk pemilihan province
    province_options = ""
    if generated_files.get('full'):
        province_options += '<option value="peta_outlet_full.html">Semua Provinsi</option>'
    
    for province, path in generated_files.get('provinces', {}).items():
        filename = os.path.basename(path)
        from multi_province_utils import get_province_emoji
        emoji = get_province_emoji(province)
        province_options += f'<option value="{filename}">{emoji} {province}</option>'
    
    # Statistik maps
    total_maps = len(generated_files.get('provinces', {}))
    if generated_files.get('full'):
        total_maps += 1
    
    # Info Indomaret untuk dashboard
    indomaret_info = ""
    if indomaret_stats:
        indomaret_info = f"""
        <div style="background: #008080; padding: 8px 15px; border-radius: 6px; font-size: 12px; color: white; margin-left: 10px;">
            <i class="fas fa-store"></i> {indomaret_stats.get('total_stores', 0)} Indomaret
        </div>
        """
    
    # Quick links untuk Indomaret dan Kecamatan
    additional_links = ""
    if generated_files.get('indomaret_report'):
        indomaret_report_filename = os.path.basename(generated_files['indomaret_report'])
        additional_links += f"""
            <a href="{indomaret_report_filename}" download class="indomaret-report">
                <i class="fas fa-chart-pie"></i> Laporan Indomaret
            </a>
        """
    
    # Link dashboard kecamatan
    kecamatan_dashboard = os.path.join(output_dir, "dashboard_analisis_kecamatan.html")
    if os.path.exists(kecamatan_dashboard):
        additional_links += f"""
            <a href="dashboard_analisis_kecamatan.html" target="_blank" class="kecamatan-dashboard">
                <i class="fas fa-map-marked-alt"></i> Dashboard Kecamatan
            </a>
        """
    
    dashboard_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Analisis Outlet - Multi Province + Indomaret</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        
        #header {{
            background: #2c3e50;
            color: white;
            padding: 15px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .header-left {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .header-logo {{
            height: 50px;
            border-radius: 5px;
        }}
        
        .header-title {{
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0;
        }}
        
        .province-selector {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .province-selector select {{
            padding: 8px 15px;
            border-radius: 6px;
            border: 1px solid #bdc3c7;
            background: white;
            font-size: 14px;
            font-weight: 500;
            min-width: 200px;
            cursor: pointer;
        }}
        
        .stats-info {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .stats-info > div {{
            background: #34495e;
            padding: 8px 15px;
            border-radius: 6px;
            font-size: 12px;
        }}
        
        #content {{
            display: flex;
            flex-direction: column;
            height: calc(100vh - 80px);
        }}
        
        #map-container {{
            flex-grow: 1;
            position: relative;
        }}
        
        #map-iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}
        
        #footer {{
            background-color: #34495e;
            color: white;
            padding: 10px 20px;
            text-align: center;
            font-size: 14px;
        }}
        
        .quick-links {{
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }}
        
        .quick-links a {{
            padding: 6px 12px;
            background: #4169E1;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 12px;
            transition: background 0.3s;
        }}
        
        .quick-links a:hover {{
            background: #1E90FF;
        }}
        
        .quick-links a.index {{
            background: #008000;
        }}
        
        .quick-links a.index:hover {{
            background: #006400;
        }}
        
        .quick-links a.indomaret-report {{
            background: #008080;
        }}
        
        .quick-links a.indomaret-report:hover {{
            background: #006666;
        }}
        
        .quick-links a.kecamatan-dashboard {{
            background: #4B0082;
        }}
        
        .quick-links a.kecamatan-dashboard:hover {{
            background: #3A006B;
        }}
        
        @media (max-width: 768px) {{
            #header {{
                flex-direction: column;
                text-align: center;
            }}
            
            .province-selector select {{
                min-width: 150px;
            }}
            
            .quick-links {{
                justify-content: center;
            }}
        }}
    </style>
</head>
<body>    
    <div id="content">
        <div id="map-container">
            <iframe id="map-iframe" src="{'peta_outlet_full.html' if generated_files.get('full') else list(generated_files.get('provinces', {}).values())[0] if generated_files.get('provinces') else 'maps_index.html'}"></iframe>
        </div>
    </div>
    
    
    <script>
    function changeMap(filename) {{
        if (filename) {{
            document.getElementById('map-iframe').src = filename;
        }}
    }}
    
    // Auto-select based on URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const selectedProvince = urlParams.get('province');
    if (selectedProvince) {{
        const select = document.getElementById('province-select');
        const option = select.querySelector(`option[value="${{selectedProvince}}"]`);
        if (option) {{
            select.value = selectedProvince;
            changeMap(selectedProvince);
        }}
    }}
    </script>
</body>
</html>
"""
    
    dashboard_output = os.path.join(output_dir, "index.html")
    
    try:
        with open(dashboard_output, 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
            
        logger.info(f"Multi-province dashboard dengan Indomaret berhasil dibuat: {dashboard_output}")
        return True
    except Exception as e:
        logger.error(f"Error saat membuat dashboard: {e}")
        return False

# Wrapper functions untuk backward compatibility
def generate_map(results, output_file=DEFAULT_OUTPUT_MAP, excel_file=None, indomaret_json_path=None):
    """
    Wrapper function yang membuat multiple maps dengan integrasi Indomaret
    """
    try:
        output_dir = os.path.dirname(output_file) if os.path.dirname(output_file) else "output"
        generated_files = generate_multi_province_maps(results, output_dir, excel_file, indomaret_json_path)
        
        # Return path ke full map untuk compatibility
        return generated_files.get('full', output_file)
        
    except Exception as e:
        logger.error(f"Error in generate_map wrapper: {e}")
        return None