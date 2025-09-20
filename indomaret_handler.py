#!/usr/bin/env python3
"""
Handler untuk mengintegrasikan data Indomaret ke dalam sistem analisis outlet
"""

import json
import os
import logging
from typing import List, Dict, Optional
from config import logger

class IndomaretHandler:
    """
    Class untuk menangani data Indomaret dan mengintegrasikannya dengan outlet analysis
    """
    
    def __init__(self, indomaret_json_path: str = "indomaret_data.json"):
        """
        Initialize Indomaret handler
        
        Parameters:
        indomaret_json_path (str): Path ke file JSON data Indomaret
        """
        self.indomaret_json_path = indomaret_json_path
        self.indomaret_data = []
        self.load_indomaret_data()
    
    def load_indomaret_data(self) -> bool:
        """
        Memuat data Indomaret dari file JSON
        
        Returns:
        bool: True jika berhasil, False jika gagal
        """
        try:
            if not os.path.exists(self.indomaret_json_path):
                logger.warning(f"File Indomaret data tidak ditemukan: {self.indomaret_json_path}")
                return False
            
            with open(self.indomaret_json_path, 'r', encoding='utf-8') as f:
                self.indomaret_data = json.load(f)
            
            logger.info(f"Berhasil memuat {len(self.indomaret_data)} data Indomaret")
            
            # Validasi format data
            if self.indomaret_data and isinstance(self.indomaret_data, list):
                required_fields = ['Store', 'Latitude', 'Longitude', 'Kecamatan']
                sample = self.indomaret_data[0]
                
                missing_fields = [field for field in required_fields if field not in sample]
                if missing_fields:
                    logger.error(f"Format data Indomaret tidak valid. Field yang hilang: {missing_fields}")
                    return False
                
                logger.info("Format data Indomaret valid")
                return True
            else:
                logger.error("Data Indomaret tidak dalam format list yang valid")
                return False
                
        except Exception as e:
            logger.error(f"Error saat memuat data Indomaret: {e}")
            return False
    
    def get_indomaret_by_radius(self, outlet_lat: float, outlet_lon: float, radius_km: float = 0.5) -> List[Dict]:
        """
        Mendapatkan daftar Indomaret dalam radius tertentu dari koordinat outlet
        
        Parameters:
        outlet_lat (float): Latitude outlet
        outlet_lon (float): Longitude outlet
        radius_km (float): Radius pencarian dalam kilometer (default: 2km)
        
        Returns:
        List[Dict]: Daftar Indomaret dalam radius tersebut dengan jarak
        """
        if not self.indomaret_data:
            return []
        
        from geopy.distance import geodesic
        
        outlet_coords = (outlet_lat, outlet_lon)
        nearby_stores = []
        
        for store in self.indomaret_data:
            try:
                store_lat = store.get('Latitude')
                store_lon = store.get('Longitude')
                
                # Skip jika koordinat tidak valid
                if store_lat is None or store_lon is None:
                    continue
                
                # Konversi ke float jika masih string
                if isinstance(store_lat, str):
                    store_lat = float(store_lat)
                if isinstance(store_lon, str):
                    store_lon = float(store_lon)
                
                store_coords = (store_lat, store_lon)
                distance = geodesic(outlet_coords, store_coords).kilometers
                
                if distance <= radius_km:
                    # Tambahkan jarak ke data store
                    store_with_distance = store.copy()
                    store_with_distance['Distance_KM'] = round(distance, 3)
                    nearby_stores.append(store_with_distance)
                    
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid coordinates for store {store.get('Store', 'Unknown')}: {e}")
                continue
        
        # Urutkan berdasarkan jarak terdekat
        nearby_stores.sort(key=lambda x: x['Distance_KM'])
        
        logger.info(f"Ditemukan {len(nearby_stores)} Indomaret dalam radius {radius_km}km dari outlet")
        
        return nearby_stores
    
    def get_all_kecamatan(self) -> List[str]:
        """
        Mendapatkan daftar semua kecamatan yang ada di data Indomaret
        
        Returns:
        List[str]: Daftar nama kecamatan
        """
        if not self.indomaret_data:
            return []
        
        kecamatan_set = set()
        for store in self.indomaret_data:
            kecamatan_raw = store.get('Kecamatan', '')
            # Handle None values
            if kecamatan_raw is None:
                kecamatan = ''
            else:
                kecamatan = str(kecamatan_raw).strip()
            
            if kecamatan:
                kecamatan_set.add(kecamatan.upper())
        
        return sorted(list(kecamatan_set))
    
    def get_indomaret_statistics(self) -> Dict:
        """
        Mendapatkan statistik data Indomaret
        
        Returns:
        Dict: Statistik data Indomaret
        """
        if not self.indomaret_data:
            return {
                'total_stores': 0,
                'total_kecamatan': 0,
                'stores_per_kecamatan': {}
            }
        
        kecamatan_count = {}
        for store in self.indomaret_data:
            kecamatan_raw = store.get('Kecamatan', '')
            # Handle None values dan pastikan string
            if kecamatan_raw is None:
                kecamatan = ''
            else:
                kecamatan = str(kecamatan_raw).strip().upper()
            
            if kecamatan:
                kecamatan_count[kecamatan] = kecamatan_count.get(kecamatan, 0) + 1
        
        return {
            'total_stores': len(self.indomaret_data),
            'total_kecamatan': len(kecamatan_count),
            'stores_per_kecamatan': kecamatan_count
        }
    
    def enhance_outlet_data_with_indomaret(self, outlet_results: List[Dict], radius_km: float = 0.5) -> List[Dict]:
        """
        Menambahkan informasi Indomaret ke data outlet berdasarkan radius jarak
        
        Parameters:
        outlet_results (List[Dict]): Data hasil analisis outlet
        radius_km (float): Radius pencarian dalam kilometer (default: 2km)
        
        Returns:
        List[Dict]: Data outlet yang sudah diperkaya dengan info Indomaret
        """
        if not self.indomaret_data:
            logger.warning("Data Indomaret tidak tersedia, skip enhancement")
            return outlet_results
        
        enhanced_results = []
        matched_count = 0
        total_indomaret_found = 0
        
        logger.info(f"Mencari Indomaret dalam radius {radius_km}km dari setiap outlet...")
        
        for i, outlet in enumerate(outlet_results):
            enhanced_outlet = outlet.copy()
            
            try:
                # Ambil koordinat outlet
                outlet_lat = outlet.get('Latitude')
                outlet_lon = outlet.get('Longitude')
                
                if outlet_lat is None or outlet_lon is None:
                    logger.warning(f"Outlet {outlet.get('Nama Outlet', 'Unknown')} tidak memiliki koordinat valid")
                    enhanced_outlet['Indomaret_Count'] = 0
                    enhanced_outlet['Indomaret_Stores'] = []
                    enhanced_outlet['Has_Indomaret'] = False
                    enhanced_results.append(enhanced_outlet)
                    continue
                
                # Cari Indomaret dalam radius
                nearby_indomaret = self.get_indomaret_by_radius(outlet_lat, outlet_lon, radius_km)
                
                # Tambahkan info Indomaret ke outlet
                enhanced_outlet['Indomaret_Count'] = len(nearby_indomaret)
                enhanced_outlet['Indomaret_Stores'] = nearby_indomaret
                enhanced_outlet['Has_Indomaret'] = len(nearby_indomaret) > 0
                enhanced_outlet['Indomaret_Search_Radius_KM'] = radius_km
                
                if len(nearby_indomaret) > 0:
                    matched_count += 1
                    total_indomaret_found += len(nearby_indomaret)
                    closest_distance = nearby_indomaret[0]['Distance_KM']
                    logger.info(f"✅ Outlet {i+1}/{len(outlet_results)} '{outlet.get('Nama Outlet', 'Unknown')}': {len(nearby_indomaret)} Indomaret (terdekat: {closest_distance}km)")
                else:
                    logger.info(f"❌ Outlet {i+1}/{len(outlet_results)} '{outlet.get('Nama Outlet', 'Unknown')}': 0 Indomaret dalam radius {radius_km}km")
                    
            except Exception as e:
                logger.error(f"Error processing outlet {outlet.get('Nama Outlet', 'Unknown')}: {e}")
                enhanced_outlet['Indomaret_Count'] = 0
                enhanced_outlet['Indomaret_Stores'] = []
                enhanced_outlet['Has_Indomaret'] = False
                
            enhanced_results.append(enhanced_outlet)
        
        # Log summary
        logger.info("=" * 50)
        logger.info("📊 RINGKASAN INTEGRASI INDOMARET (RADIUS)")
        logger.info("=" * 50)
        logger.info(f"✅ {matched_count} outlet memiliki Indomaret dalam radius {radius_km}km")
        logger.info(f"❌ {len(enhanced_results) - matched_count} outlet tidak ada Indomaret dalam radius")
        logger.info(f"🏪 Total {total_indomaret_found} Indomaret ditemukan di sekitar outlet")
        logger.info(f"📍 Rata-rata {total_indomaret_found/len(enhanced_results):.1f} Indomaret per outlet")
        
        return enhanced_results
    
    def create_indomaret_popup(self, store: Dict) -> str:
        """
        Membuat popup HTML untuk marker Indomaret
        
        Parameters:
        store (Dict): Data store Indomaret
        
        Returns:
        str: HTML popup
        """
        store_name = store.get('Store', 'Indomaret')
        kecamatan_raw = store.get('Kecamatan', 'Unknown')
        
        # Handle None values
        if kecamatan_raw is None:
            kecamatan = 'Unknown'
        else:
            kecamatan = str(kecamatan_raw)
        
        lat = store.get('Latitude', 0)
        lon = store.get('Longitude', 0)
        
        # Pastikan koordinat valid
        if lat is None:
            lat = 0
        if lon is None:
            lon = 0
        
    def create_indomaret_popup_with_distance(self, store: Dict, distance_km: float) -> str:
        """
        Membuat popup HTML untuk marker Indomaret dengan informasi jarak
        
        Parameters:
        store (Dict): Data store Indomaret
        distance_km (float): Jarak dalam kilometer
        
        Returns:
        str: HTML popup
        """
        store_name = store.get('Store', 'Indomaret')
        kecamatan_raw = store.get('Kecamatan', 'Unknown')
        
        # Handle None values
        if kecamatan_raw is None:
            kecamatan = 'Unknown'
        else:
            kecamatan = str(kecamatan_raw)
        
        lat = store.get('Latitude', 0)
        lon = store.get('Longitude', 0)
        
        # Pastikan koordinat valid
        if lat is None:
            lat = 0
        if lon is None:
            lon = 0
        
        # Buat link ke Google Maps
        gmaps_url = f"https://www.google.com/maps?q={lat},{lon}"
        
        # Tentukan status jarak untuk radius 500m
        if distance_km <= 0.1:
            distance_status = "Sangat Dekat"
            distance_color = "#27ae60"
            distance_icon = "🔥"
        elif distance_km <= 0.3:
            distance_status = "Dekat"
            distance_color = "#f39c12"
            distance_icon = "👍"
        elif distance_km <= 0.5:
            distance_status = "Moderate"
            distance_color = "#3498db"
            distance_icon = "📍"
        else:
            distance_status = "Jauh"
            distance_color = "#95a5a6"
            distance_icon = "📏"
        
        popup_html = f"""
        <div style="min-width: 280px; max-width: 320px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            <div style="background: #1e88e5; color: white; padding: 15px; margin: -9px -9px 12px -9px; border-radius: 8px 8px 0 0;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="background: white; padding: 5px; border-radius: 4px;">
                        <span style="color: #1e88e5; font-weight: bold; font-size: 12px;">INDOMARET</span>
                    </div>
                    <h4 style="margin: 0; font-size: 14px; font-weight: bold;">Toko Indomaret</h4>
                </div>
                <div style="margin-top: 8px; font-size: 12px; opacity: 0.9;">
                    🏪 Convenience Store
                </div>
            </div>
            
            <div style="background: {distance_color}; color: white; padding: 10px; border-radius: 6px; margin-bottom: 12px; text-align: center;">
                <div style="font-weight: bold; font-size: 14px;">
                    {distance_icon} {distance_status}
                </div>
                <div style="font-size: 12px; opacity: 0.9; margin-top: 2px;">
                    {distance_km} km dari outlet
                </div>
            </div>
            
            <div style="margin-bottom: 12px; padding: 12px; background: #f5f5f5; border-radius: 6px;">
                <div style="font-size: 13px; color: #333; margin-bottom: 8px;">
                    <strong>📍 Nama Toko:</strong><br>
                    <span style="font-size: 12px; color: #666;">{store_name}</span>
                </div>
                <div style="font-size: 13px; color: #333;">
                    <strong>🏘️ Kecamatan:</strong> {kecamatan}
                </div>
            </div>
            
            <div style="margin-bottom: 12px; padding: 10px; background: #e3f2fd; border-radius: 6px; border-left: 4px solid #1e88e5;">
                <div style="font-size: 12px; color: #1565c0;">
                    <strong>📍 Koordinat:</strong> {lat:.6f}, {lon:.6f}
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 15px;">
                <a href="{gmaps_url}" target="_blank" 
                   style="display: inline-block; padding: 10px 16px; background: #1e88e5; color: white; 
                   text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 12px;
                   transition: background 0.3s;">
                    <i class="fa fa-external-link"></i> Buka di Google Maps
                </a>
            </div>
            
            <div style="margin-top: 12px; text-align: center; font-size: 10px; color: #999; 
                        padding: 8px; background: #f8f9fa; border-radius: 4px;">
                💡 Indomaret dalam radius pencarian dari outlet
            </div>
        </div>
        """
        
        return popup_html
        
        popup_html = f"""
        <div style="min-width: 280px; max-width: 320px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            <div style="background: #1e88e5; color: white; padding: 15px; margin: -9px -9px 12px -9px; border-radius: 8px 8px 0 0;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="background: white; padding: 5px; border-radius: 4px;">
                        <span style="color: #1e88e5; font-weight: bold; font-size: 12px;">INDOMARET</span>
                    </div>
                    <h4 style="margin: 0; font-size: 14px; font-weight: bold;">Toko Indomaret</h4>
                </div>
                <div style="margin-top: 8px; font-size: 12px; opacity: 0.9;">
                    🏪 Convenience Store
                </div>
            </div>
            
            <div style="margin-bottom: 12px; padding: 12px; background: #f5f5f5; border-radius: 6px;">
                <div style="font-size: 13px; color: #333; margin-bottom: 8px;">
                    <strong>📍 Nama Toko:</strong><br>
                    <span style="font-size: 12px; color: #666;">{store_name}</span>
                </div>
                <div style="font-size: 13px; color: #333;">
                    <strong>🏘️ Kecamatan:</strong> {kecamatan}
                </div>
            </div>
            
            <div style="margin-bottom: 12px; padding: 10px; background: #e3f2fd; border-radius: 6px; border-left: 4px solid #1e88e5;">
                <div style="font-size: 12px; color: #1565c0;">
                    <strong>📍 Koordinat:</strong> {lat:.6f}, {lon:.6f}
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 15px;">
                <a href="{gmaps_url}" target="_blank" 
                   style="display: inline-block; padding: 10px 16px; background: #1e88e5; color: white; 
                   text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 12px;
                   transition: background 0.3s;">
                    <i class="fa fa-external-link"></i> Buka di Google Maps
                </a>
            </div>
            
            <div style="margin-top: 12px; text-align: center; font-size: 10px; color: #999; 
                        padding: 8px; background: #f8f9fa; border-radius: 4px;">
                💡 Data Indomaret di kecamatan yang sama dengan outlet
            </div>
        </div>
        """
        
        return popup_html
    
    def add_indomaret_markers_to_map(self, folium_map, outlet_lat: float, outlet_lon: float, radius_km: float = 0.5):
        """
        Menambahkan marker Indomaret ke peta berdasarkan radius dari outlet
        
        Parameters:
        folium_map: Folium map object
        outlet_lat (float): Latitude outlet
        outlet_lon (float): Longitude outlet
        radius_km (float): Radius pencarian dalam kilometer
        
        Returns:
        int: Jumlah marker yang ditambahkan
        """
        try:
            import folium
        except ImportError:
            logger.error("Folium tidak tersedia, tidak dapat menambahkan marker Indomaret")
            return 0
        
        nearby_stores = self.get_indomaret_by_radius(outlet_lat, outlet_lon, radius_km)
        
        if not nearby_stores:
            logger.info(f"Tidak ada Indomaret dalam radius {radius_km}km dari outlet")
            return 0
        
        markers_added = 0
        
        for store in nearby_stores:
            try:
                lat = store.get('Latitude')
                lon = store.get('Longitude')
                distance = store.get('Distance_KM', 0)
                
                if lat is None or lon is None:
                    logger.warning(f"Koordinat tidak valid untuk store: {store.get('Store', 'Unknown')}")
                    continue
                
                # Buat popup untuk Indomaret dengan jarak
                popup_html = self.create_indomaret_popup_with_distance(store, distance)
                
                # Tentukan warna marker berdasarkan jarak (untuk radius 500m)
                if distance <= 0.1:
                    marker_color = 'darkblue'  # Sangat dekat (≤100m)
                elif distance <= 0.3:
                    marker_color = 'blue'      # Dekat (≤300m)
                else:
                    marker_color = 'lightblue' # Agak jauh (≤500m)
                
                # Tambahkan marker Indomaret dengan icon khusus
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=350),
                    tooltip=f"🏪 Indomaret ({distance}km): {store.get('Store', 'Unknown')}",
                    icon=folium.Icon(
                        color=marker_color,
                        icon='shopping-cart',
                        prefix='fa'
                    )
                ).add_to(folium_map)
                
                markers_added += 1
                
            except Exception as e:
                logger.warning(f"Error menambahkan marker Indomaret {store.get('Store', 'Unknown')}: {e}")
                continue
        
        logger.info(f"Berhasil menambahkan {markers_added} marker Indomaret dalam radius {radius_km}km")
        return markers_added
    
    def generate_indomaret_report(self, outlet_results: List[Dict]) -> Dict:
        """
        Membuat laporan tentang distribusi Indomaret relatif terhadap outlet
        
        Parameters:
        outlet_results (List[Dict]): Data outlet yang sudah diperkaya dengan info Indomaret
        
        Returns:
        Dict: Laporan distribusi Indomaret
        """
        if not outlet_results:
            return {}
        
        # Statistik dasar
        total_outlets = len(outlet_results)
        outlets_with_indomaret = sum(1 for outlet in outlet_results if outlet.get('Has_Indomaret', False))
        outlets_without_indomaret = total_outlets - outlets_with_indomaret
        
        # Hitung total Indomaret di kecamatan dengan outlet
        total_indomaret_in_outlet_areas = sum(outlet.get('Indomaret_Count', 0) for outlet in outlet_results)
        
        # Distribusi per kecamatan
        kecamatan_distribution = {}
        for outlet in outlet_results:
            kecamatan = outlet.get('Kecamatan', 'Unknown')
            if kecamatan not in kecamatan_distribution:
                kecamatan_distribution[kecamatan] = {
                    'outlets': 0,
                    'indomaret_stores': 0,
                    'outlets_with_indomaret': 0
                }
            
            kecamatan_distribution[kecamatan]['outlets'] += 1
            kecamatan_distribution[kecamatan]['indomaret_stores'] += outlet.get('Indomaret_Count', 0)
            if outlet.get('Has_Indomaret', False):
                kecamatan_distribution[kecamatan]['outlets_with_indomaret'] += 1
        
        # Kecamatan dengan Indomaret terbanyak
        top_indomaret_kecamatan = sorted(
            kecamatan_distribution.items(), 
            key=lambda x: x[1]['indomaret_stores'], 
            reverse=True
        )[:5]
        
        # Kecamatan tanpa Indomaret
        kecamatan_without_indomaret = [
            kecamatan for kecamatan, data in kecamatan_distribution.items()
            if data['indomaret_stores'] == 0
        ]
        
        report = {
            'summary': {
                'total_outlets': total_outlets,
                'outlets_with_indomaret': outlets_with_indomaret,
                'outlets_without_indomaret': outlets_without_indomaret,
                'percentage_with_indomaret': (outlets_with_indomaret / total_outlets * 100) if total_outlets > 0 else 0,
                'total_indomaret_in_outlet_areas': total_indomaret_in_outlet_areas
            },
            'kecamatan_distribution': kecamatan_distribution,
            'top_indomaret_kecamatan': top_indomaret_kecamatan,
            'kecamatan_without_indomaret': kecamatan_without_indomaret,
            'insights': self._generate_insights(kecamatan_distribution, outlets_with_indomaret, total_outlets)
        }
        
        return report
    
    def _generate_insights(self, kecamatan_distribution: Dict, outlets_with_indomaret: int, total_outlets: int) -> Dict:
        """
        Generate business insights dari data Indomaret
        
        Parameters:
        kecamatan_distribution (Dict): Distribusi per kecamatan
        outlets_with_indomaret (int): Jumlah outlet dengan Indomaret
        total_outlets (int): Total outlet
        
        Returns:
        Dict: Business insights
        """
        insights = {}
        
        # Competition analysis
        competition_level = "RENDAH"
        if outlets_with_indomaret / total_outlets > 0.7:
            competition_level = "TINGGI"
        elif outlets_with_indomaret / total_outlets > 0.4:
            competition_level = "SEDANG"
        
        insights['competition_analysis'] = f"Tingkat kompetisi dengan Indomaret: {competition_level}. " \
                                         f"{outlets_with_indomaret} dari {total_outlets} outlet berada di kecamatan yang juga memiliki Indomaret."
        
        # Market opportunity
        kecamatan_without_indomaret = [k for k, d in kecamatan_distribution.items() if d['indomaret_stores'] == 0 and d['outlets'] > 0]
        
        if kecamatan_without_indomaret:
            insights['market_opportunity'] = f"Peluang pasar: {len(kecamatan_without_indomaret)} kecamatan memiliki outlet tapi belum ada Indomaret. " \
                                           f"Kecamatan tersebut: {', '.join(kecamatan_without_indomaret[:3])}{'...' if len(kecamatan_without_indomaret) > 3 else ''}"
        else:
            insights['market_opportunity'] = "Semua kecamatan dengan outlet sudah memiliki Indomaret sebagai kompetitor."
        
        # Strategic recommendation
        high_competition_areas = [k for k, d in kecamatan_distribution.items() if d['indomaret_stores'] > 3]
        
        if high_competition_areas:
            insights['strategic_recommendation'] = f"Rekomendasi strategis: Fokus diferensiasi produk di {len(high_competition_areas)} kecamatan dengan kompetisi Indomaret tinggi (>3 toko). " \
                                                 f"Kecamatan: {', '.join(high_competition_areas[:2])}{'...' if len(high_competition_areas) > 2 else ''}"
        else:
            insights['strategic_recommendation'] = "Peluang ekspansi masih terbuka di sebagian besar area tanpa kompetisi Indomaret yang ketat."
        
        return insights


def create_sample_indomaret_data():
    """
    Membuat contoh file data Indomaret untuk testing
    """
    sample_data = [
        {
            "Store": "A. M. SANGAJI - AMBON(T4IU)",
            "Latitude": -3.697586,
            "Longitude": 128.179656,
            "Kecamatan": "SIRIMAU"
        },
        {
            "Store": "AHURU - AMBON(T6FQ)",
            "Latitude": -3.689239,
            "Longitude": 128.206658,
            "Kecamatan": "SIRIMAU"
        },
        {
            "Store": "JAKARTA PUSAT - MENTENG(A1B2)",
            "Latitude": -6.195,
            "Longitude": 106.829,
            "Kecamatan": "MENTENG"
        },
        {
            "Store": "YOGYAKARTA - BANTUL(C3D4)",
            "Latitude": -7.888,
            "Longitude": 110.330,
            "Kecamatan": "BANTUL"
        }
    ]
    
    sample_file = "sample_indomaret_data.json"
    
    try:
        with open(sample_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)
        
        print(f"File contoh data Indomaret berhasil dibuat: {sample_file}")
        return sample_file
    except Exception as e:
        print(f"Error membuat file contoh: {e}")
        return None


if __name__ == "__main__":
    # Demo penggunaan
    print("=== DEMO INDOMARET HANDLER ===")
    
    # Buat file contoh jika belum ada
    if not os.path.exists("indomaret_data.json"):
        print("File indomaret_data.json tidak ditemukan, membuat file contoh...")
        create_sample_indomaret_data()
    
    # Test IndomaretHandler
    handler = IndomaretHandler("indomaret_data.json")
    
    if handler.indomaret_data:
        # Tampilkan statistik
        stats = handler.get_indomaret_statistics()
        print(f"\nStatistik data Indomaret:")
        print(f"Total stores: {stats['total_stores']}")
        print(f"Total kecamatan: {stats['total_kecamatan']}")
        
        # Test pencarian berdasarkan kecamatan
        test_kecamatan = "SIRIMAU"
        stores = handler.get_indomaret_by_kecamatan(test_kecamatan)
        print(f"\nIndomaret di kecamatan {test_kecamatan}: {len(stores)} toko")
        for store in stores:
            print(f"  - {store['Store']}")
    else:
        print("Gagal memuat data Indomaret")