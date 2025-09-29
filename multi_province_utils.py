"""
Utilities untuk mendukung pembuatan multiple maps per provinsi
"""

import os
import json
from datetime import datetime
from config import (
    PROVINCE_BOUNDS, get_province_filename, get_province_map_filename,
    get_all_province_map_files, logger, NAVIGATION_STYLE
)

def group_outlets_by_province(results):
    """
    Mengelompokkan outlet berdasarkan provinsi
    
    Parameters:
    results (list): Hasil analisis outlet
    
    Returns:
    dict: Dictionary dengan provinsi sebagai key dan list outlet sebagai value
    """
    from map_generator import get_province_from_coordinates
    
    outlets_by_province = {}
    
    for outlet in results:
        lat, lon = outlet['Latitude'], outlet['Longitude']
        province = get_province_from_coordinates(lat, lon)
        
        if province not in outlets_by_province:
            outlets_by_province[province] = []
        outlets_by_province[province].append(outlet)
    
    logger.info(f"Outlets dikelompokkan ke dalam {len(outlets_by_province)} provinsi")
    for province, outlets in outlets_by_province.items():
        logger.info(f"  {province}: {len(outlets)} outlets")
    
    return outlets_by_province

def create_navigation_dropdown(current_province=None, base_dir="", include_full=True):
    """
    Membuat dropdown navigation untuk berpindah antar provinsi
    
    Parameters:
    current_province (str): Provinsi yang sedang aktif
    base_dir (str): Base directory untuk file
    include_full (bool): Sertakan opsi "Semua Provinsi"
    
    Returns:
    str: HTML dropdown navigation
    """
    dropdown_html = f"""
     <div style="position: fixed; top: 20px; left: 450px; z-index: 1000;">
            <img src="/logo.png" alt="Logo" style="width: 100px;border-radius: 5px;">
        </div>
    <div style="position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 1000; 
         background: #2c3e50; padding: 15px 20px; border-radius: 10px; 
         box-shadow: 0 4px 20px rgba(0,0,0,0.3); border: 1px solid #34495e;">
        
        <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap; justify-content: center;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="fa fa-map-marked-alt" style="color: #3498db; font-size: 18px;"></i>
                <span style="color: #ecf0f1; font-weight: 600; font-size: 16px;">Pilih Provinsi:</span>
            </div>
            
            <select id="province-selector" onchange="changeProvince(this.value)" 
                    style="padding: 8px 15px; border-radius: 6px; border: 1px solid #bdc3c7; 
                    background: white; font-size: 14px; font-weight: 500; min-width: 200px; cursor: pointer;">
    """
    
    if include_full:
        selected_full = 'selected' if current_province is None or current_province == 'SEMUA' else ''
        dropdown_html += f'<option value="full" {selected_full}> Semua Provinsi</option>'
    
    for province in PROVINCE_BOUNDS.keys():
        selected = 'selected' if current_province == province else ''
        province_file = get_province_map_filename(province)
        emoji = get_province_emoji(province)
        dropdown_html += f'<option value="{province_file}" {selected}>{emoji} {province}</option>'
    
    dropdown_html += f"""
            </select>
            
            <div style="display: flex; align-items: center; gap: 8px; background: #34495e; 
                        padding: 6px 12px; border-radius: 6px;">
                <i class="fa fa-eye" style="color: #f39c12; font-size: 14px;"></i>
                <span style="color: #ecf0f1; font-size: 12px; font-weight: 500;">
                    {get_current_province_display(current_province)}
                </span>
            </div>
        </div>
    </div>
    
    <script>
    function changeProvince(filename) {{
        if (filename === 'full') {{
            window.location.href = 'peta_outlet_full.html';
        }} else {{
            window.location.href = filename;
        }}
    }}
    </script>
    """
    
    return dropdown_html

def create_navigation_tabs(current_province=None, base_dir="", include_full=True):
    """
    Membuat tab navigation untuk berpindah antar provinsi
    
    Parameters:
    current_province (str): Provinsi yang sedang aktif
    base_dir (str): Base directory untuk file
    include_full (bool): Sertakan tab "Semua Provinsi"
    
    Returns:
    str: HTML tab navigation
    """
    tabs_html = f"""
    <div style="position: fixed; top: 20px; left: 20px; right: 20px; z-index: 1000; 
         background: #2c3e50; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); 
         border: 1px solid #34495e; overflow: hidden;">
        
        <div style="display: flex; overflow-x: auto; padding: 5px;">
    """
    
    if include_full:
        active_class = 'active-tab' if current_province is None or current_province == 'SEMUA' else ''
        tabs_html += f"""
            <a href="peta_outlet_full.html" class="nav-tab {active_class}" 
               style="display: flex; align-items: center; gap: 6px; padding: 10px 15px; 
               text-decoration: none; color: #ecf0f1; font-size: 13px; font-weight: 500; 
               border-radius: 6px; margin: 2px; white-space: nowrap; transition: all 0.3s;
               background: {'#3498db' if active_class else 'transparent'};">
                <i class="fa fa-globe-asia"></i>
                <span>Semua</span>
            </a>
        """
    
    for province in PROVINCE_BOUNDS.keys():
        active_class = 'active-tab' if current_province == province else ''
        province_file = get_province_map_filename(province)
        emoji = get_province_emoji(province)
        short_name = get_province_short_name(province)
        
        tabs_html += f"""
            <a href="{province_file}" class="nav-tab {active_class}" 
               style="display: flex; align-items: center; gap: 6px; padding: 10px 15px; 
               text-decoration: none; color: #ecf0f1; font-size: 13px; font-weight: 500; 
               border-radius: 6px; margin: 2px; white-space: nowrap; transition: all 0.3s;
               background: {'#3498db' if active_class else 'transparent'};">
                <span>{emoji}</span>
                <span>{short_name}</span>
            </a>
        """
    
    tabs_html += """
        </div>
    </div>
    
    <style>
    .nav-tab:hover {
        background: #34495e !important;
    }
    .nav-tab.active-tab {
        background: #3498db !important;
    }
    </style>
    """
    
    return tabs_html

def get_province_emoji(province):
    """
    Mendapatkan emoji untuk provinsi
    
    Parameters:
    province (str): Nama provinsi
    
    Returns:
    str: Emoji untuk provinsi
    """
    emoji_map = {
        'JAKARTA': '🏙️',
        'JAWA BARAT': '🏔️', 
        'JAWA TENGAH': '🏛️',
        'SUMBAGSEL': '🌴',
        'SUMBAGUT': '🌿',
        'JATIMBANUSKAL': '🏝️',
        'SULTER': '🌺'
    }
    return emoji_map.get(province, '📍')

def get_province_short_name(province):
    """
    Mendapatkan nama pendek provinsi untuk UI
    
    Parameters:
    province (str): Nama provinsi
    
    Returns:
    str: Nama pendek provinsi
    """
    short_name_map = {
        'JAKARTA': 'Jakarta',
        'JAWA BARAT': 'Jabar', 
        'JAWA TENGAH': 'Jateng',
        'SUMBAGSEL': 'Sumsel',
        'SUMBAGUT': 'Sumut',
        'JATIMBANUSKAL': 'Jatimbalikal',
        'SULTER': 'Sulter'
    }
    return short_name_map.get(province, province)

def get_current_province_display(current_province):
    """
    Mendapatkan display text untuk provinsi yang sedang aktif
    
    Parameters:
    current_province (str): Provinsi yang aktif
    
    Returns:
    str: Display text
    """
    if current_province is None or current_province == 'SEMUA':
        return "Menampilkan Semua Provinsi"
    else:
        return f"Fokus: {current_province}"

def create_province_navigation(current_province=None, style=None, base_dir="", include_full=True):
    """
    Membuat navigation berdasarkan style yang dipilih
    
    Parameters:
    current_province (str): Provinsi yang sedang aktif
    style (str): Style navigasi ("dropdown" atau "tabs")
    base_dir (str): Base directory untuk file
    include_full (bool): Sertakan opsi semua provinsi
    
    Returns:
    str: HTML navigation
    """
    if style is None:
        style = NAVIGATION_STYLE
    
    if style == "tabs":
        return create_navigation_tabs(current_province, base_dir, include_full)
    else:
        return create_navigation_dropdown(current_province, base_dir, include_full)

def create_province_info_panel(province, outlets_count, facilities_count):
    """
    Membuat info panel khusus untuk provinsi
    
    Parameters:
    province (str): Nama provinsi
    outlets_count (int): Jumlah outlet di provinsi
    facilities_count (int): Jumlah fasilitas di provinsi
    
    Returns:
    str: HTML info panel
    """
    province_config = PROVINCE_BOUNDS.get(province)
    emoji = get_province_emoji(province)
    
    info_panel = f"""
    <div style="position: fixed; bottom: {90 if NAVIGATION_STYLE == 'tabs' else 100}px; left: 20px; z-index: 1000; 
         background: #2c3e50; color: #ecf0f1; padding: 20px; border-radius: 10px; 
         box-shadow: 0 4px 20px rgba(0,0,0,0.3); max-width: 350px; 
         border: 1px solid #34495e;">
        
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 15px;">
            <div style="background: #3498db; padding: 8px; border-radius: 6px; font-size: 20px;">
                {emoji}
            </div>
            <div>
                <h3 style="margin: 0; font-size: 18px; font-weight: 600;">{province}</h3>
                <div style="font-size: 12px; color: #bdc3c7; margin-top: 2px;">Provinsi Focus Map</div>
            </div>
        </div>
        
        <div style="background: #34495e; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #e67e22;"> Data Provinsi:</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px;">
                <div style="text-align: center; padding: 8px; background: #2c3e50; border-radius: 4px;">
                    <div style="font-weight: bold; color: #3498db;">{outlets_count}</div>
                    <div style="color: #bdc3c7;">Outlets</div>
                </div>
                <div style="text-align: center; padding: 8px; background: #2c3e50; border-radius: 4px;">
                    <div style="font-weight: bold; color: #e67e22;">{facilities_count}</div>
                    <div style="color: #bdc3c7;">Fasilitas</div>
                </div>
            </div>
        </div>
    </div>

    """

    return info_panel

def save_province_map_metadata(output_dir, outlets_by_province):
    """
    Menyimpan metadata tentang maps per provinsi
    
    Parameters:
    output_dir (str): Direktori output
    outlets_by_province (dict): Data outlet per provinsi
    
    Returns:
    bool: True jika berhasil
    """
    try:
        metadata = {
            'generated_at': datetime.now().isoformat(),
            'navigation_style': NAVIGATION_STYLE,
            'provinces': {},
            'files': {}
        }
        
        # Province info
        for province, outlets in outlets_by_province.items():
            if province in PROVINCE_BOUNDS:
                facilities_count = 0
                for outlet in outlets:
                    detailed_facilities = outlet.get('detailed_facilities', {})
                    facilities_count += sum(len(places) for places in detailed_facilities.values())
                
                metadata['provinces'][province] = {
                    'outlets_count': len(outlets),
                    'facilities_count': facilities_count,
                    'config': PROVINCE_BOUNDS[province],
                    'filename': get_province_map_filename(province)
                }
        
        # File mappings
        metadata['files'] = {
            'full_map': 'peta_outlet_full.html',
            'province_maps': get_all_province_map_files()
        }
        
        # Save metadata
        metadata_file = os.path.join(output_dir, 'province_maps_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Province maps metadata saved to {metadata_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving province maps metadata: {e}")
        return False

def validate_province_data(outlets_by_province):
    """
    Validasi data outlet per provinsi
    
    Parameters:
    outlets_by_province (dict): Data outlet per provinsi
    
    Returns:
    dict: Hasil validasi
    """
    validation_result = {
        'valid': True,
        'warnings': [],
        'errors': [],
        'summary': {}
    }
    
    total_outlets = sum(len(outlets) for outlets in outlets_by_province.values())
    configured_provinces = set(PROVINCE_BOUNDS.keys())
    data_provinces = set(outlets_by_province.keys())
    
    # Check untuk provinsi yang tidak dikonfigurasi
    unconfigured_provinces = data_provinces - configured_provinces
    if unconfigured_provinces:
        validation_result['warnings'].append(
            f"Provinsi tidak dikonfigurasi: {unconfigured_provinces}. Maps tidak akan dibuat untuk provinsi ini."
        )
    
    # Check untuk provinsi yang dikonfigurasi tapi tidak ada data
    empty_provinces = configured_provinces - data_provinces
    if empty_provinces:
        validation_result['warnings'].append(
            f"Provinsi dikonfigurasi tapi tidak ada data: {empty_provinces}"
        )
    
    # Summary
    validation_result['summary'] = {
        'total_outlets': total_outlets,
        'total_provinces_with_data': len(data_provinces),
        'configured_provinces': len(configured_provinces),
        'maps_to_generate': len(data_provinces.intersection(configured_provinces))
    }
    
    logger.info(f"Province data validation: {validation_result['summary']}")
    for warning in validation_result['warnings']:
        logger.warning(warning)
    
    return validation_result