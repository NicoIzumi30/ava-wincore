import requests
import time
import pickle
import os
import random
from config import (
    OVERPASS_ENDPOINTS, API_TIMEOUT, ENABLE_CACHE, 
    CACHE_FILE, USE_SIMPLIFIED_QUERIES, logger
)

# Global cache untuk menyimpan hasil API
api_cache = {}

def load_cache():
    """
    Memuat cache API dari file jika ada
    """
    global api_cache
    if ENABLE_CACHE and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                api_cache = pickle.load(f)
            logger.info(f"Loaded API cache with {len(api_cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            api_cache = {}

def save_cache():
    """
    Menyimpan cache API ke file
    """
    if ENABLE_CACHE:
        try:
            with open(CACHE_FILE, 'wb') as f:
                pickle.dump(api_cache, f)
            logger.info(f"Saved API cache with {len(api_cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

def get_simplified_queries():
    """
    Versi query yang lebih sederhana untuk menghemat waktu API
    """
    return {
        'residential': '[out:json][timeout:15]; (way["landuse"="residential"](around:{radius},{lat},{lon}); way["building"~"residential|apartments|house|dormitory"](around:{radius},{lat},{lon}); node["building"~"residential|apartments|house|dormitory"](around:{radius},{lat},{lon}); node["name"~"perumahan|apartemen|rumah susun|asrama|cluster|villa"](around:{radius},{lat},{lon}); way["name"~"perumahan|apartemen|rumah susun|asrama|cluster|villa"](around:{radius},{lat},{lon}); ); out body;',
        
        'education': '[out:json][timeout:15]; (node["amenity"~"school|university|college|kindergarten"](around:{radius},{lat},{lon}); way["amenity"~"school|university|college|kindergarten"](around:{radius},{lat},{lon}); node["building"~"school|university|college"](around:{radius},{lat},{lon}); way["building"~"school|university|college"](around:{radius},{lat},{lon}); node["name"~"SD|SMP|SMA|Universitas|TK|PAUD|Pesantren|Lembaga kursus|Sekolah"](around:{radius},{lat},{lon}); way["name"~"SD|SMP|SMA|Universitas|TK|PAUD|Pesantren|Lembaga kursus|Sekolah"](around:{radius},{lat},{lon}); ); out body;',
        
        'public_area': '[out:json][timeout:15]; (node["amenity"~"park|community_centre|marketplace|place_of_worship|bus_station|terminal|hospital|clinic|doctors|healthcare"](around:{radius},{lat},{lon}); way["amenity"~"park|community_centre|marketplace|place_of_worship|bus_station|terminal|hospital|clinic|doctors|healthcare"](around:{radius},{lat},{lon}); node["leisure"="park"](around:{radius},{lat},{lon}); way["leisure"="park"](around:{radius},{lat},{lon}); node["public_transport"](around:{radius},{lat},{lon}); node["tourism"="museum"](around:{radius},{lat},{lon}); way["tourism"="museum"](around:{radius},{lat},{lon}); node["healthcare"](around:{radius},{lat},{lon}); way["healthcare"](around:{radius},{lat},{lon}); node["name"~"taman kota|alun-alun|stasiun|terminal|tempat ibadah|museum|rumah sakit|hospital|klinik|puskesmas|poliklinik|rs|clinic"](around:{radius},{lat},{lon}); way["name"~"taman kota|alun-alun|stasiun|terminal|tempat ibadah|museum|rumah sakit|hospital|klinik|puskesmas|poliklinik|rs|clinic"](around:{radius},{lat},{lon}); ); out body;',
        
        'culinary': '[out:json][timeout:15]; (node["amenity"~"restaurant|cafe|food_court|fast_food"](around:{radius},{lat},{lon}); way["amenity"~"restaurant|cafe|food_court|fast_food"](around:{radius},{lat},{lon}); node["shop"~"bakery|coffee|tea|convenience"](around:{radius},{lat},{lon}); way["shop"~"bakery|coffee|tea|convenience"](around:{radius},{lat},{lon}); node["cuisine"](around:{radius},{lat},{lon}); way["cuisine"](around:{radius},{lat},{lon}); node["name"~"restoran|warung makan|kedai kopi|street food|food court|cafe|rumah makan|warteg|kantin|warmindo|warung|kedai|mie ayam|bakso|nasi|pecel|soto|es krim|ice cream|minuman|kafe|coffee|tea|teh|jus|juice|ayam|chicken|burger|pizza|seafood|steak|depot|eatery|kopi|padang|catering|martabak|bakery|kue|roti"](around:{radius},{lat},{lon}); way["name"~"restoran|warung makan|kedai kopi|street food|food court|cafe|rumah makan|warteg|kantin|warmindo|warung|kedai|mie ayam|bakso|nasi|pecel|soto|es krim|ice cream|minuman|kafe|coffee|tea|teh|jus|juice|ayam|chicken|burger|pizza|seafood|steak|depot|eatery|kopi|padang|catering|martabak|bakery|kue|roti"](around:{radius},{lat},{lon}); ); out body;',
        
        'business_center': '[out:json][timeout:15]; (node["shop"](around:{radius},{lat},{lon}); way["shop"](around:{radius},{lat},{lon}); node["building"~"commercial|office|retail|supermarket|industrial"](around:{radius},{lat},{lon}); way["building"~"commercial|office|retail|supermarket|industrial"](around:{radius},{lat},{lon}); node["amenity"="marketplace"](around:{radius},{lat},{lon}); way["amenity"="marketplace"](around:{radius},{lat},{lon}); node["office"](around:{radius},{lat},{lon}); way["office"](around:{radius},{lat},{lon}); node["shop"~"mall|supermarket|department_store"](around:{radius},{lat},{lon}); way["shop"~"mall|supermarket|department_store"](around:{radius},{lat},{lon}); node["name"~"gedung perkantoran|ruko|kawasan industri|coworking space|perkantoran|mall|plaza|pusat pembelanjaan|shopping center|shopping mall|department store|hypermarket|supermarket|retail|indomaret|alfamart|alfamidi|pertokoan|pasar|market"](around:{radius},{lat},{lon}); way["name"~"gedung perkantoran|ruko|kawasan industri|coworking space|perkantoran|mall|plaza|pusat pembelanjaan|shopping center|shopping mall|department store|hypermarket|supermarket|retail|indomaret|alfamart|alfamidi|pertokoan|pasar|market"](around:{radius},{lat},{lon}); ); out body;',
        
        # Kategori baru: groceries
        'groceries': '[out:json][timeout:15]; (node["shop"~"supermarket|grocery|greengrocer|butcher|seafood|deli|spices|bakery"](around:{radius},{lat},{lon}); way["shop"~"supermarket|grocery|greengrocer|butcher|seafood|deli|spices|bakery"](around:{radius},{lat},{lon}); node["name"~"toko kelontong|toko sembako|toko sayur|mini market|mini mart|fresh market|pasar tradisional|supermarket|grocery|greengrocer|butcher|seafood|deli|spices"](around:{radius},{lat},{lon}); way["name"~"toko kelontong|toko sembako|toko sayur|mini market|mini mart|fresh market|pasar tradisional|supermarket|grocery|greengrocer|butcher|seafood|deli|spices"](around:{radius},{lat},{lon}); ); out body;',
        
        # Kategori baru: convenient stores
        'convenient_stores': '[out:json][timeout:15]; (node["shop"~"convenience"](around:{radius},{lat},{lon}); way["shop"~"convenience"](around:{radius},{lat},{lon}); node["name"~"indomaret|alfamart|alfamidi|circle k|family mart|lawson|7-eleven|7 eleven|seven eleven|minimart|mini mart|mini market|convenience store"](around:{radius},{lat},{lon}); way["name"~"indomaret|alfamart|alfamidi|circle k|family mart|lawson|7-eleven|7 eleven|seven eleven|minimart|mini mart|mini market|convenience store"](around:{radius},{lat},{lon}); ); out body;',
        
        # Kategori baru: industrial/factory
        'industrial': '[out:json][timeout:15]; (node["landuse"~"industrial"](around:{radius},{lat},{lon}); way["landuse"~"industrial"](around:{radius},{lat},{lon}); node["building"~"industrial|factory|warehouse"](around:{radius},{lat},{lon}); way["building"~"industrial|factory|warehouse"](around:{radius},{lat},{lon}); node["industrial"](around:{radius},{lat},{lon}); way["industrial"](around:{radius},{lat},{lon}); node["name"~"pabrik|factory|industri|industrial|warehousing|pergudangan|gudang|warehouse|manufacturing|kawasan industri|workshop|bengkel"](around:{radius},{lat},{lon}); way["name"~"pabrik|factory|industri|industrial|warehousing|pergudangan|gudang|warehouse|manufacturing|kawasan industri|workshop|bengkel"](around:{radius},{lat},{lon}); ); out body;',
        
        # Kategori baru: hospital/clinic
        'hospital_clinic': '[out:json][timeout:15]; (node["amenity"~"hospital|clinic|doctors|healthcare"](around:{radius},{lat},{lon}); way["amenity"~"hospital|clinic|doctors|healthcare"](around:{radius},{lat},{lon}); node["healthcare"](around:{radius},{lat},{lon}); way["healthcare"](around:{radius},{lat},{lon}); node["building"="hospital"](around:{radius},{lat},{lon}); way["building"="hospital"](around:{radius},{lat},{lon}); node["name"~"rumah sakit|hospital|klinik|clinic|puskesmas|bidan|dokter|doctor|medical center|pusat kesehatan|rs|apotek|apotik|pharmacy|medical"](around:{radius},{lat},{lon}); way["name"~"rumah sakit|hospital|klinik|clinic|puskesmas|bidan|dokter|doctor|medical center|pusat kesehatan|rs|apotek|apotik|pharmacy|medical"](around:{radius},{lat},{lon}); ); out body;'
    }

def get_comprehensive_queries():
    """
    Versi query yang lebih lengkap untuk hasil yang lebih akurat
    """
    return {
        'residential': '[out:json][timeout:30]; (node["building"~"residential|apartments|house|dormitory"](around:{radius},{lat},{lon}); way["building"~"residential|apartments|house|dormitory"](around:{radius},{lat},{lon}); way["landuse"="residential"](around:{radius},{lat},{lon}); node["amenity"="housing"](around:{radius},{lat},{lon}); way["amenity"="housing"](around:{radius},{lat},{lon}); node["name"~"perumahan|apartemen|rumah susun|asrama|cluster|villa|apartment|residence|housing|dormitory"](around:{radius},{lat},{lon}); way["name"~"perumahan|apartemen|rumah susun|asrama|cluster|villa|apartment|residence|housing|dormitory"](around:{radius},{lat},{lon}); ); out body;',
        
        'education': '[out:json][timeout:30]; (node["amenity"~"school|university|college|kindergarten|language_school|education|training"](around:{radius},{lat},{lon}); way["amenity"~"school|university|college|kindergarten|language_school|education|training"](around:{radius},{lat},{lon}); node["building"~"school|university|college|kindergarten|education"](around:{radius},{lat},{lon}); way["building"~"school|university|college|kindergarten|education"](around:{radius},{lat},{lon}); node["name"~"SD|SMP|SMA|SMK|Universitas|TK|PAUD|Pesantren|Lembaga kursus|Sekolah|School|University|College|Academy|Institute|Pendidikan|Education|Training|Kursus|Course"](around:{radius},{lat},{lon}); way["name"~"SD|SMP|SMA|SMK|Universitas|TK|PAUD|Pesantren|Lembaga kursus|Sekolah|School|University|College|Academy|Institute|Pendidikan|Education|Training|Kursus|Course"](around:{radius},{lat},{lon}); ); out body;',
        
        'public_area': '[out:json][timeout:30]; (node["amenity"~"park|community_centre|marketplace|place_of_worship|bus_station|terminal|bus_stop|ferry_terminal|transportation|public_building|hospital|clinic|doctors|healthcare"](around:{radius},{lat},{lon}); way["amenity"~"park|community_centre|marketplace|place_of_worship|bus_station|terminal|bus_stop|ferry_terminal|transportation|public_building|hospital|clinic|doctors|healthcare"](around:{radius},{lat},{lon}); node["leisure"~"park|garden|playground"](around:{radius},{lat},{lon}); way["leisure"~"park|garden|playground"](around:{radius},{lat},{lon}); node["public_transport"](around:{radius},{lat},{lon}); way["public_transport"](around:{radius},{lat},{lon}); node["tourism"~"museum|gallery|attraction"](around:{radius},{lat},{lon}); way["tourism"~"museum|gallery|attraction"](around:{radius},{lat},{lon}); node["healthcare"](around:{radius},{lat},{lon}); way["healthcare"](around:{radius},{lat},{lon}); node["building"="hospital"](around:{radius},{lat},{lon}); way["building"="hospital"](around:{radius},{lat},{lon}); node["name"~"taman kota|alun-alun|stasiun|terminal|tempat ibadah|museum|masjid|gereja|pura|vihara|klenteng|mosque|church|temple|synagogue|park|square|station|terminal|public area|public space|rumah sakit|hospital|klinik|puskesmas|poliklinik|rs|clinic|health center|medical center"](around:{radius},{lat},{lon}); way["name"~"taman kota|alun-alun|stasiun|terminal|tempat ibadah|museum|masjid|gereja|pura|vihara|klenteng|mosque|church|temple|synagogue|park|square|station|terminal|public area|public space|rumah sakit|hospital|klinik|puskesmas|poliklinik|rs|clinic|health center|medical center"](around:{radius},{lat},{lon}); node["aeroway"](around:{radius},{lat},{lon}); way["aeroway"](around:{radius},{lat},{lon}); ); out body;',
        
        'culinary': '[out:json][timeout:30]; (node["amenity"~"restaurant|cafe|food_court|fast_food|pub|bar|bistro"](around:{radius},{lat},{lon}); way["amenity"~"restaurant|cafe|food_court|fast_food|pub|bar|bistro"](around:{radius},{lat},{lon}); node["shop"~"bakery|coffee|tea|convenience|grocery|supermarket|food"](around:{radius},{lat},{lon}); way["shop"~"bakery|coffee|tea|convenience|grocery|supermarket|food"](around:{radius},{lat},{lon}); node["cuisine"](around:{radius},{lat},{lon}); way["cuisine"](around:{radius},{lat},{lon}); node["name"~"restoran|warung makan|kedai kopi|street food|food court|cafe|restaurant|warung|warteg|rumah makan|kantin|angkringan|kedai|bakery|bakeri|kue|roti|makanan|minuman|kuliner|catering|dapur|food|coffee|kopi|makan|padang|stall|canteen|warmindo|warung|warung mie|warung bakso|warung nasi|fried chicken|ayam goreng|ayam geprek|burger|pizza|steakhouse|bbq|barbecue|seafood|aneka|jus|juice|minuman|milk|tea|teh|ice cream|es krim|martabak|depot|eatery|bakso|mie ayam|bebek|seafood|nasi|gado-gado|sate|satay|soto|gulai|rendang|pecel|warteg|padang|bistro|kebab"](around:{radius},{lat},{lon}); way["name"~"restoran|warung makan|kedai kopi|street food|food court|cafe|restaurant|warung|warteg|rumah makan|kantin|angkringan|kedai|bakery|bakeri|kue|roti|makanan|minuman|kuliner|catering|dapur|food|coffee|kopi|makan|padang|stall|canteen|warmindo|warung|warung mie|warung bakso|warung nasi|fried chicken|ayam goreng|ayam geprek|burger|pizza|steakhouse|bbq|barbecue|seafood|aneka|jus|juice|minuman|milk|tea|teh|ice cream|es krim|martabak|depot|eatery|bakso|mie ayam|bebek|seafood|nasi|gado-gado|sate|satay|soto|gulai|rendang|pecel|warteg|padang|bistro|kebab"](around:{radius},{lat},{lon}); ); out body;',
        
        'business_center': '[out:json][timeout:30]; (node["shop"](around:{radius},{lat},{lon}); way["shop"](around:{radius},{lat},{lon}); node["building"~"commercial|office|retail|supermarket|industrial|warehouse|factory"](around:{radius},{lat},{lon}); way["building"~"commercial|office|retail|supermarket|industrial|warehouse|factory"](around:{radius},{lat},{lon}); node["amenity"~"marketplace|bank|atm|bureau_de_change|business_center"](around:{radius},{lat},{lon}); way["amenity"~"marketplace|bank|atm|bureau_de_change|business_center"](around:{radius},{lat},{lon}); node["office"](around:{radius},{lat},{lon}); way["office"](around:{radius},{lat},{lon}); node["industrial"](around:{radius},{lat},{lon}); way["industrial"](around:{radius},{lat},{lon}); node["landuse"~"commercial|retail|industrial"](around:{radius},{lat},{lon}); way["landuse"~"commercial|retail|industrial"](around:{radius},{lat},{lon}); node["shop"~"mall|supermarket|department_store|convenience|marketplace"](around:{radius},{lat},{lon}); way["shop"~"mall|supermarket|department_store|convenience|marketplace"](around:{radius},{lat},{lon}); node["name"~"gedung perkantoran|ruko|kawasan industri|coworking space|perkantoran|office building|office tower|mall|plaza|pusat bisnis|business center|factory|warehouse|gudang|pasar|market|shop|toko|retail|store|supermarket|minimarket|alfamart|indomaret|alfamidi|mini market|department store|industrial|industry|pusat perbelanjaan|shopping center|shopping mall|plaza|square|trade center|ITC|mangga dua|tanah abang|pasar|market|bazaar|hypermarket|carrefour|giant|lotte mart|ramayana|matahari|metro|transmart|grand indonesia|central park|pondok indah|teras kota"](around:{radius},{lat},{lon}); way["name"~"gedung perkantoran|ruko|kawasan industri|coworking space|perkantoran|office building|office tower|mall|plaza|pusat bisnis|business center|factory|warehouse|gudang|pasar|market|shop|toko|retail|store|supermarket|minimarket|alfamart|indomaret|alfamidi|mini market|department store|industrial|industry|pusat perbelanjaan|shopping center|shopping mall|plaza|square|trade center|ITC|mangga dua|tanah abang|pasar|market|bazaar|hypermarket|carrefour|giant|lotte mart|ramayana|matahari|metro|transmart|grand indonesia|central park|pondok indah|teras kota"](around:{radius},{lat},{lon}); ); out body;',
        
        # Kategori baru: groceries
        'groceries': '[out:json][timeout:30]; (node["shop"~"supermarket|grocery|greengrocer|butcher|seafood|deli|spices|bakery|convenience|food"](around:{radius},{lat},{lon}); way["shop"~"supermarket|grocery|greengrocer|butcher|seafood|deli|spices|bakery|convenience|food"](around:{radius},{lat},{lon}); node["amenity"="marketplace"](around:{radius},{lat},{lon}); way["amenity"="marketplace"](around:{radius},{lat},{lon}); node["name"~"toko kelontong|toko sembako|toko sayur|mini market|mini mart|fresh market|pasar tradisional|supermarket|hypermarket|grocery|greengrocer|butcher|seafood|deli|spices|bakery|pasar|market|swalayan|toserba|giant|carrefour|lottemart|ranch market|farmers market|transmart|hero|brastagi|foodmart|foodhall|organic|food market|superindo|grand lucky|total buah|buah|sayur|vegetables|fruits|meat|daging|food|makanan|pasaraya|fresh|segar|toko buah|grocery|groceries|buah segar|minimarket|foodmart|grosir|wholesale|retail|super indo"](around:{radius},{lat},{lon}); way["name"~"toko kelontong|toko sembako|toko sayur|mini market|mini mart|fresh market|pasar tradisional|supermarket|hypermarket|grocery|greengrocer|butcher|seafood|deli|spices|bakery|pasar|market|swalayan|toserba|giant|carrefour|lottemart|ranch market|farmers market|transmart|hero|brastagi|foodmart|foodhall|organic|food market|superindo|grand lucky|total buah|buah|sayur|vegetables|fruits|meat|daging|food|makanan|pasaraya|fresh|segar|toko buah|grocery|groceries|buah segar|minimarket|foodmart|grosir|wholesale|retail|super indo"](around:{radius},{lat},{lon}); ); out body;',
        
        # Kategori baru: convenient stores
        'convenient_stores': '[out:json][timeout:30]; (node["shop"~"convenience|kiosk"](around:{radius},{lat},{lon}); way["shop"~"convenience|kiosk"](around:{radius},{lat},{lon}); node["amenity"="marketplace"](around:{radius},{lat},{lon}); way["amenity"="marketplace"](around:{radius},{lat},{lon}); node["name"~"indomaret|alfamart|alfamidi|circle k|family mart|lawson|7-eleven|7 eleven|seven eleven|minimart|mini mart|mini market|convenience store|convenience|toko kelontong|warung|warung kelontong|kios|kiosk|toko|mart|eceran|ritel|minishop|toko serba ada|toko kecil|wartel|kiosco|retail|alfaexpress|alfa midi|alfa express|indomart|alfaexpress|alfa|indomaret point"](around:{radius},{lat},{lon}); way["name"~"indomaret|alfamart|alfamidi|circle k|family mart|lawson|7-eleven|7 eleven|seven eleven|minimart|mini mart|mini market|convenience store|convenience|toko kelontong|warung|warung kelontong|kios|kiosk|toko|mart|eceran|ritel|minishop|toko serba ada|toko kecil|wartel|kiosco|retail|alfaexpress|alfa midi|alfa express|indomart|alfaexpress|alfa|indomaret point"](around:{radius},{lat},{lon}); ); out body;',
        
        # Kategori baru: industrial/factory
        'industrial': '[out:json][timeout:30]; (node["landuse"~"industrial|factory"](around:{radius},{lat},{lon}); way["landuse"~"industrial|factory"](around:{radius},{lat},{lon}); node["building"~"industrial|factory|warehouse|manufacture|manufacturing"](around:{radius},{lat},{lon}); way["building"~"industrial|factory|warehouse|manufacture|manufacturing"](around:{radius},{lat},{lon}); node["industrial"~"factory|zone|area|estate|manufacturing|workshop"](around:{radius},{lat},{lon}); way["industrial"~"factory|zone|area|estate|manufacturing|workshop"](around:{radius},{lat},{lon}); node["man_made"~"works|factory"](around:{radius},{lat},{lon}); way["man_made"~"works|factory"](around:{radius},{lat},{lon}); node["name"~"pabrik|factory|industri|industrial|warehousing|pergudangan|gudang|warehouse|manufacturing|kawasan industri|workshop|bengkel|industrial estate|industrial complex|industrial park|industrial area|manufacture|logistic|logistik|manufacturing|assembly|assembling|processing|storage|fabrikasi|fabrication|plant|kilang|depot|garasi|maintenance|pemeliharaan|perbaikan|repair|machining|welding|galvanizing|forge|foundry|smelter|refinery|kiln|mill|manufaktur"](around:{radius},{lat},{lon}); way["name"~"pabrik|factory|industri|industrial|warehousing|pergudangan|gudang|warehouse|manufacturing|kawasan industri|workshop|bengkel|industrial estate|industrial complex|industrial park|industrial area|manufacture|logistic|logistik|manufacturing|assembly|assembling|processing|storage|fabrikasi|fabrication|plant|kilang|depot|garasi|maintenance|pemeliharaan|perbaikan|repair|machining|welding|galvanizing|forge|foundry|smelter|refinery|kiln|mill|manufaktur"](around:{radius},{lat},{lon}); ); out body;',
        
        # Kategori baru: hospital/clinic
        'hospital_clinic': '[out:json][timeout:30]; (node["amenity"~"hospital|clinic|doctors|healthcare|dentist|pharmacy|veterinary|health_centre"](around:{radius},{lat},{lon}); way["amenity"~"hospital|clinic|doctors|healthcare|dentist|pharmacy|veterinary|health_centre"](around:{radius},{lat},{lon}); node["healthcare"](around:{radius},{lat},{lon}); way["healthcare"](around:{radius},{lat},{lon}); node["building"~"hospital|clinic|healthcare"](around:{radius},{lat},{lon}); way["building"~"hospital|clinic|healthcare"](around:{radius},{lat},{lon}); node["emergency"="yes"](around:{radius},{lat},{lon}); way["emergency"="yes"](around:{radius},{lat},{lon}); node["name"~"rumah sakit|hospital|klinik|clinic|puskesmas|bidan|dokter|doctor|medical center|pusat kesehatan|rs|apotek|apotik|pharmacy|medical|klinik gigi|dental|dentist|orthodontist|poliklinik|laboratorium|lab|laboratory|radiologi|radiology|ambulance|ambulans|ICU|IGD|UGD|emergency|physiotherapy|fisioterapi|rehab|rehabilitasi|rehabilitation|psikiatri|psychiatry|psikologi|psychology|mental health|kesehatan jiwa|health|medical service|layanan kesehatan|specialist|spesialis|care|nursing|perawatan|therapy|terapi|orthopaedic|orthopedic|optometrist|eye|mata|neurology|saraf|children|anak|ginekologi|obstetri|kanker|cancer|kardiovaskular|cardiovascular|jantung|heart|internist|internal|kulit|skin|urologi|urology|fertility|reproduksi|bedah|surgery|aesthetics|kecantikan|darurat|intensive|trauma"](around:{radius},{lat},{lon}); way["name"~"rumah sakit|hospital|klinik|clinic|puskesmas|bidan|dokter|doctor|medical center|pusat kesehatan|rs|apotek|apotik|pharmacy|medical|klinik gigi|dental|dentist|orthodontist|poliklinik|laboratorium|lab|laboratory|radiologi|radiology|ambulance|ambulans|ICU|IGD|UGD|emergency|physiotherapy|fisioterapi|rehab|rehabilitasi|rehabilitation|psikiatri|psychiatry|psikologi|psychology|mental health|kesehatan jiwa|health|medical service|layanan kesehatan|specialist|spesialis|care|nursing|perawatan|therapy|terapi|orthopaedic|orthopedic|optometrist|eye|mata|neurology|saraf|children|anak|ginekologi|obstetri|kanker|cancer|kardiovaskular|cardiovascular|jantung|heart|internist|internal|kulit|skin|urologi|urology|fertility|reproduksi|bedah|surgery|aesthetics|kecantikan|darurat|intensive|trauma"](around:{radius},{lat},{lon}); ); out body;'
    }

def analyze_element_for_categories(tags, name):
    """
    Menganalisis tag dan nama elemen untuk menentukan kategorinya
    
    Parameters:
    tags (dict): Tag dari elemen
    name (str): Nama dari elemen, kosong jika tidak ada
    
    Returns:
    dict: Dictionary berisi kategori dan status keberadaan (True/False)
    """
    result = {
        'residential': False,
        'education': False,
        'public_area': False,
        'culinary': False,
        'business_center': False,
        'groceries': False,           # Kategori baru
        'convenient_stores': False,   # Kategori baru
        'industrial': False,          # Kategori baru
        'hospital_clinic': False      # Kategori baru
    }
    
    # Mengkonversi nama ke lowercase untuk perbandingan yang lebih baik
    name_lower = name.lower() if name else ""
    
    # Cek Residential
    if (tags.get("building") in ["residential", "apartments", "house", "dormitory"] or
        tags.get("landuse") == "residential" or
        tags.get("amenity") == "housing" or
        any(keyword in name_lower for keyword in ["perumahan", "apartemen", "rumah susun", "asrama", "cluster", "villa", "apartment", "residence", "housing", "dormitory"])):
        result['residential'] = True
    
    # Cek Education
    if (tags.get("amenity") in ["school", "university", "college", "kindergarten", "language_school", "education", "training"] or
        tags.get("building") in ["school", "university", "college", "kindergarten", "education"] or
        any(keyword in name_lower for keyword in ["sd", "smp", "sma", "smk", "universitas", "tk", "paud", "pesantren", "lembaga kursus", "sekolah", "school", "university", "college", "academy", "institute", "pendidikan", "education", "training", "kursus", "course"])):
        result['education'] = True
    
    # Cek Public Area
    if (tags.get("amenity") in ["park", "community_centre", "marketplace", "place_of_worship", "bus_station", "terminal", "bus_stop", "ferry_terminal", "transportation", "public_building"] or
        tags.get("leisure") in ["park", "garden", "playground"] or
        tags.get("tourism") in ["museum", "gallery", "attraction"] or
        "public_transport" in tags or
        tags.get("aeroway") in ["aerodrome", "terminal"] or
        any(keyword in name_lower for keyword in ["taman kota", "alun-alun", "stasiun", "terminal", "tempat ibadah", "museum", "masjid", "gereja", "pura", "vihara", "klenteng","mosque", "church", "temple", "synagogue", "park", "square", "station", "public area", "public space"])):
        result['public_area'] = True
    
    # Cek Culinary
    if (tags.get("amenity") in ["restaurant", "cafe", "food_court", "fast_food", "bar", "pub", "bistro"] or
        tags.get("shop") in ["bakery", "coffee", "tea", "convenience", "grocery", "supermarket", "food"] or
        "cuisine" in tags or
        any(keyword in name_lower for keyword in [
            "restoran", "warung makan", "kedai kopi", "street food", "food court", "cafe", "restaurant", 
            "warung", "warteg", "rumah makan", "kantin", "angkringan", "kedai", "bakery", "bakeri", "kue", 
            "roti", "makanan", "minuman", "kuliner", "catering", "dapur", "food", "coffee", "kopi", "makan", 
            "padang", "stall", "canteen", "warmindo", "warung mie", "warung bakso", "warung nasi", 
            "fried chicken", "ayam goreng", "ayam geprek", "burger", "pizza", "steakhouse", "bbq", 
            "barbecue", "seafood", "aneka", "jus", "juice", "minuman", "milk", "tea", "teh", "ice cream", 
            "es krim", "martabak", "depot", "eatery", "bakso", "mie ayam", "bebek", "seafood", "nasi", 
            "gado-gado", "sate", "satay", "soto", "gulai", "rendang", "pecel", "padang", "bistro", "kebab"
        ])):
        result['culinary'] = True
    
    # Cek Business Center
    if (tags.get("shop") or
        tags.get("building") in ["commercial", "office", "retail", "supermarket"] or
        tags.get("amenity") in ["marketplace", "bank", "atm", "bureau_de_change", "business_center"] or
        "office" in tags or
        tags.get("shop") in ["mall", "supermarket", "department_store", "convenience", "marketplace"] or
        tags.get("landuse") in ["commercial", "retail"] or
        any(keyword in name_lower for keyword in [
            "gedung perkantoran", "ruko", "coworking space", "perkantoran", "office building", 
            "office tower", "mall", "plaza", "pusat bisnis", "business center", "pasar", "market", "shop", 
            "toko", "retail", "store", "supermarket", "department store", "pusat perbelanjaan", 
            "shopping center", "shopping mall", "plaza", "square", "trade center", "itc", "mangga dua", 
            "tanah abang", "pasar", "market", "bazaar", "hypermarket", "carrefour", "giant", "lotte mart", 
            "ramayana", "matahari", "metro", "transmart", "grand indonesia", "central park", "pondok indah", 
            "teras kota"
        ])):
        result['business_center'] = True
    
    # Cek Groceries (kategori baru)
    if (tags.get("shop") in ["supermarket", "grocery", "greengrocer", "butcher", "seafood", "deli", "spices", "bakery", "food"] or
        tags.get("amenity") == "marketplace" or
        any(keyword in name_lower for keyword in [
            "toko kelontong", "toko sembako", "toko sayur", "mini market", "mini mart", "fresh market", 
            "pasar tradisional", "supermarket", "hypermarket", "grocery", "greengrocer", "butcher", "seafood", 
            "deli", "spices", "bakery", "pasar", "market", "swalayan", "toserba", "giant", "carrefour", 
            "lottemart", "ranch market", "farmers market", "transmart", "hero", "brastagi", "foodmart", "foodhall", 
            "organic", "food market", "superindo", "grand lucky", "total buah", "buah", "sayur", "vegetables", 
            "fruits", "meat", "daging", "food", "makanan", "pasaraya", "fresh", "segar", "toko buah", "grocery", 
            "groceries", "buah segar", "minimarket", "foodmart", "grosir", "wholesale", "retail", "super indo"
        ])):
        result['groceries'] = True
    
    # Cek Convenient Stores (kategori baru)
    if (tags.get("shop") in ["convenience", "kiosk"] or
        any(keyword in name_lower for keyword in [
            "indomaret", "alfamart", "alfamidi", "circle k", "family mart", "lawson", "7-eleven", "7 eleven", 
            "seven eleven", "minimart", "mini mart", "mini market", "convenience store", "convenience", 
            "toko kelontong", "warung kelontong", "kios", "kiosk", "toko", "mart", "eceran", "ritel", "minishop", 
            "toko serba ada", "toko kecil", "wartel", "kiosco", "retail", "alfaexpress", "alfa midi", "alfa express", 
            "indomart", "alfaexpress", "alfa", "indomaret point"
        ])):
        result['convenient_stores'] = True
    
    # Cek Industrial/Factory (kategori baru)
    if (tags.get("landuse") in ["industrial", "factory"] or
        tags.get("building") in ["industrial", "factory", "warehouse", "manufacture", "manufacturing"] or
        "industrial" in tags or
        tags.get("man_made") in ["works", "factory"] or
        any(keyword in name_lower for keyword in [
            "pabrik", "factory", "industri", "industrial", "warehousing", "pergudangan", "gudang", "warehouse", 
            "manufacturing", "kawasan industri", "workshop", "bengkel", "industrial estate", "industrial complex", 
            "industrial park", "industrial area", "manufacture", "logistic", "logistik", "manufacturing", "assembly", 
            "assembling", "processing", "storage", "fabrikasi", "fabrication", "plant", "kilang", "depot", "garasi", 
            "maintenance", "pemeliharaan", "perbaikan", "repair", "machining", "welding", "galvanizing", "forge", 
            "foundry", "smelter", "refinery", "kiln", "mill", "manufaktur"
        ])):
        result['industrial'] = True
    
    # Cek Hospital/Clinic (kategori baru)
    if (tags.get("amenity") in ["hospital", "clinic", "doctors", "healthcare", "dentist", "pharmacy", "veterinary", "health_centre"] or
        "healthcare" in tags or
        tags.get("building") in ["hospital", "clinic", "healthcare"] or
        tags.get("emergency") == "yes" or
        any(keyword in name_lower for keyword in [
            "rumah sakit", "hospital", "klinik", "clinic", "puskesmas", "bidan", "dokter", "doctor", "medical center", 
            "pusat kesehatan", "rs", "apotek", "apotik", "pharmacy", "medical", "klinik gigi", "dental", "dentist", 
            "orthodontist", "poliklinik", "laboratorium", "lab", "laboratory", "radiologi", "radiology", "ambulance", 
            "ambulans", "icu", "igd", "ugd", "emergency", "physiotherapy", "fisioterapi", "rehab", "rehabilitasi", 
            "rehabilitation", "psikiatri", "psychiatry", "psikologi", "psychology", "mental health", "kesehatan jiwa", 
            "health", "medical service", "layanan kesehatan", "specialist", "spesialis", "care", "nursing", "perawatan", 
            "therapy", "terapi", "orthopaedic", "orthopedic", "optometrist", "eye", "mata", "neurology", "saraf", 
            "children", "anak", "ginekologi", "obstetri", "kanker", "cancer", "kardiovaskular", "cardiovascular", 
            "jantung", "heart", "internist", "internal", "kulit", "skin", "urologi", "urology", "fertility", "reproduksi", 
            "bedah", "surgery", "aesthetics", "kecantikan", "darurat", "intensive", "trauma"
        ])):
        result['hospital_clinic'] = True
    
    return result

def call_overpass_api(query):
    """
    Memanggil Overpass API dengan query tertentu
    
    Parameters:
    query (str): Query Overpass API
    
    Returns:
    dict: Hasil dari API atau None jika gagal
    """
    # Coba endpoint secara berurutan sampai berhasil
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            # Kurangi delay untuk mempercepat proses
            time.sleep(0.2 + random.random() * 0.3)  # Random delay 0.2-0.5 detik untuk menghindari rate limiting
            
            headers = {
                'User-Agent': 'OutletAnalysisTool/1.0 (research purpose)',
                'Accept': 'application/json'
            }
            
            logger.debug(f"Sending query to {endpoint}")
            response = requests.post(endpoint, data=query, headers=headers, timeout=API_TIMEOUT)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Status code {response.status_code} from {endpoint}")
                # Coba endpoint berikutnya jika gagal
                continue
                
        except Exception as e:
            logger.warning(f"Error with endpoint {endpoint}: {e}")
            # Coba endpoint berikutnya jika gagal
            continue
    
    # Semua endpoint gagal
    return None

def check_nearby_facilities_simple(lat, lon, radius=100):
    """
    Memeriksa fasilitas di sekitar koordinat
    
    Parameters:
    lat (float): Koordinat latitude
    lon (float): Koordinat longitude
    radius (int): Radius pencarian dalam meter
    
    Returns:
    dict: Dictionary berisi kategori dan status keberadaan (True/False)
    """
    # Cek apakah hasil sudah ada di cache
    cache_key = f"{lat},{lon},{radius}"
    if ENABLE_CACHE and cache_key in api_cache:
        logger.info(f"Using cached result for {cache_key}")
        return api_cache[cache_key]
    
    # Kategori yang akan diperiksa dengan tag yang relevan - dipilih berdasarkan preferensi kecepatan
    category_queries = get_simplified_queries() if USE_SIMPLIFIED_QUERIES else get_comprehensive_queries()
    
    # Hasil pengecekan untuk setiap kategori
    results = {
        'residential': False,
        'education': False,
        'public_area': False,
        'culinary': False,
        'business_center': False,
        'groceries': False,           # Kategori baru
        'convenient_stores': False,   # Kategori baru
        'industrial': False,          # Kategori baru
        'hospital_clinic': False      # Kategori baru
    }
    
    # Check semua kategori dalam satu query untuk mempercepat
    if not USE_SIMPLIFIED_QUERIES:
        # Deteksi dengan satu query besar untuk semua kategori
        all_categories_query = '[out:json][timeout:30]; ('
        for category, query_template in category_queries.items():
            # Format query dengan koordinat dan radius tetapi hapus header dan footer
            query_content = query_template.format(radius=radius, lat=lat, lon=lon)
            query_content = query_content.replace('[out:json][timeout:30]; (', '').replace('); out body;', '')
            all_categories_query += query_content
        all_categories_query += '); out body;'
        
        # Panggil API
        data = call_overpass_api(all_categories_query)
        
        if data:
            elements = data.get("elements", [])
            
            # Analisis hasil untuk menentukan kategori
            for element in elements:
                tags = element.get("tags", {})
                name = tags.get("name", "")
                
                # Gunakan fungsi analisis kategori
                element_categories = analyze_element_for_categories(tags, name)
                
                # Gabungkan hasil
                for category in results:
                    if element_categories[category]:
                        results[category] = True
                
                # Hentikan pencarian jika semua kategori sudah ditemukan
                if all(results.values()):
                    break
            
            # Simpan ke cache
            if ENABLE_CACHE:
                api_cache[cache_key] = results.copy()
                # Simpan cache ke file secara periodik
                if len(api_cache) % 10 == 0:
                    save_cache()
            
            return results
    
    # Jika query gabungan gagal atau tidak digunakan, coba per kategori
    # Check setiap kategori secara terpisah
    for category, query_template in category_queries.items():
        # Format query dengan koordinat dan radius
        query = query_template.format(radius=radius, lat=lat, lon=lon)
        
        # Panggil API
        data = call_overpass_api(query)
        
        if data:
            elements = data.get("elements", [])
            
            # Jika ada elemen yang ditemukan, periksa lebih detail dengan analisis kategori
            if elements:
                for element in elements:
                    tags = element.get("tags", {})
                    name = tags.get("name", "")
                    
                    # Gunakan fungsi analisis kategori untuk kategori ini
                    element_categories = analyze_element_for_categories(tags, name)
                    
                    # Jika elemen ini masuk dalam kategori yang dicari
                    if element_categories[category]:
                        results[category] = True
                        break  # Keluar dari loop elemen
    
    # Simpan ke cache
    if ENABLE_CACHE:
        api_cache[cache_key] = results.copy()
        # Simpan cache ke file secara periodik
        if len(api_cache) % 10 == 0:
            save_cache()
    
    return results
# Tambahkan fungsi-fungsi baru ini ke api_handler.py

def get_detailed_facilities_around_outlet(lat, lon, outlet_facilities, radius=100):
    """
    Mendapatkan detail lokasi fasilitas yang tercentang di sekitar outlet
    
    Parameters:
    lat (float): Koordinat latitude outlet
    lon (float): Koordinat longitude outlet
    outlet_facilities (dict): Fasilitas yang tercentang untuk outlet ini
    radius (int): Radius pencarian dalam meter
    
    Returns:
    dict: Dictionary berisi detail lokasi untuk setiap kategori yang tercentang
    """
    detailed_facilities = {}
    
    # Daftar kategori yang akan dicek
    category_mapping = {
        'Residential': 'residential',
        'Education': 'education', 
        'Public Area': 'public_area',
        'Culinary': 'culinary',
        'Business Center': 'business_center',
        'Groceries': 'groceries',
        'Convenient Stores': 'convenient_stores',
        'Industrial': 'industrial',
        'Hospital/Clinic': 'hospital_clinic'
    }
    
    # Hanya ambil detail untuk kategori yang tercentang
    for category_display, category_key in category_mapping.items():
        if outlet_facilities.get(category_display, False):
            try:
                places = get_nearby_places_detail(lat, lon, category_key, radius)
                if places:
                    detailed_facilities[category_display] = places
                    logger.info(f"Found {len(places)} {category_display} locations near outlet")
            except Exception as e:
                logger.warning(f"Error getting {category_display} details: {e}")
                detailed_facilities[category_display] = []
    
    return detailed_facilities

def get_facility_marker_config():
    """
    Mendapatkan konfigurasi marker untuk setiap kategori fasilitas
    
    Returns:
    dict: Konfigurasi marker untuk setiap kategori
    """
    return {
        'Residential': {
            'color': '#4CAF50',
            'icon': 'home',
            'prefix': 'fa',
            'size': 'sm'
        },
        'Education': {
            'color': '#2196F3',
            'icon': 'graduation-cap', 
            'prefix': 'fa',
            'size': 'sm'
        },
        'Public Area': {
            'color': '#9C27B0',
            'icon': 'tree',
            'prefix': 'fa', 
            'size': 'sm'
        },
        'Culinary': {
            'color': '#FF9800',
            'icon': 'utensils',
            'prefix': 'fa',
            'size': 'sm'
        },
        'Business Center': {
            'color': '#607D8B',
            'icon': 'briefcase',
            'prefix': 'fa',
            'size': 'sm'
        },
        'Groceries': {
            'color': '#8BC34A',
            'icon': 'shopping-cart',
            'prefix': 'fa',
            'size': 'sm'
        },
        'Convenient Stores': {
            'color': '#00BCD4',
            'icon': 'shopping-basket',
            'prefix': 'fa',
            'size': 'sm'
        },
        'Industrial': {
            'color': '#795548',
            'icon': 'industry',
            'prefix': 'fa',
            'size': 'sm'
        },
        'Hospital/Clinic': {
            'color': '#F44336',
            'icon': 'plus',
            'prefix': 'fa',
            'size': 'sm'
        }
    }

def create_facility_popup(place, category):
    """
    Membuat popup HTML untuk fasilitas sekitar
    
    Parameters:
    place (dict): Data tempat/fasilitas
    category (str): Kategori fasilitas
    
    Returns:
    str: HTML popup
    """
    # Ambil konfigurasi marker untuk kategori ini
    marker_config = get_facility_marker_config().get(category, {})
    color = marker_config.get('color', '#666666')
    icon = marker_config.get('icon', 'map-marker')
    
    # Buat link ke Google Maps jika ada koordinat
    gmaps_link = ""
    if place.get('lat') and place.get('lon'):
        gmaps_url = f"https://www.google.com/maps?q={place['lat']},{place['lon']}"
        gmaps_link = f'<a href="{gmaps_url}" target="_blank" style="color: {color}; text-decoration: none;"><i class="fa fa-external-link-alt"></i> Google Maps</a>'
    
    # Buat popup HTML
    popup_html = f"""
    <div style="min-width: 250px; max-width: 300px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
        <div style="background: {color}; color: white; padding: 12px; margin: -9px -9px 12px -9px; border-radius: 6px 6px 0 0;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="fa fa-{icon}" style="font-size: 16px;"></i>
                <h4 style="margin: 0; font-size: 14px; font-weight: bold;">{place.get('name', 'Unnamed')}</h4>
            </div>
            <div style="margin-top: 5px; font-size: 12px; opacity: 0.9;">
                📍 {category}
            </div>
        </div>
        
        <div style="margin-bottom: 12px;">
            <div style="font-size: 13px; color: #555;">
                <strong>Tipe:</strong> {place.get('type', 'Unknown')}
            </div>
        </div>
        
        {f'<div style="margin-bottom: 12px;"><div style="font-size: 12px; color: #777;"><strong>Koordinat:</strong> {place["lat"]:.6f}, {place["lon"]:.6f}</div></div>' if place.get('lat') and place.get('lon') else ''}
        
        {f'<div style="text-align: center; margin-top: 12px;">{gmaps_link}</div>' if gmaps_link else ''}
        
        <div style="margin-top: 8px; text-align: center; font-size: 10px; color: #999;">
            💡 Fasilitas di sekitar outlet
        </div>
    </div>
    """
    
    return popup_html

def process_outlets_with_detailed_facilities(results, radius=100):
    """
    Memproses semua outlet untuk mendapatkan detail fasilitas sekitar
    
    Parameters:
    results (list): Hasil analisis outlet
    radius (int): Radius pencarian dalam meter
    
    Returns:
    list: Hasil dengan detail fasilitas ditambahkan
    """
    enhanced_results = []
    
    logger.info(f"Processing {len(results)} outlets for detailed facilities...")
    
    for i, outlet in enumerate(results):
        try:
            logger.info(f"Processing outlet {i+1}/{len(results)}: {outlet['Nama Outlet']}")
            
            # Copy data outlet
            enhanced_outlet = outlet.copy()
            
            # Ambil koordinat outlet
            lat = outlet['Latitude']
            lon = outlet['Longitude']
            
            # Ambil detail fasilitas yang tercentang
            detailed_facilities = get_detailed_facilities_around_outlet(
                lat, lon, outlet, radius
            )
            
            # Tambahkan detail fasilitas ke data outlet
            enhanced_outlet['detailed_facilities'] = detailed_facilities
            
            enhanced_results.append(enhanced_outlet)
            
            # Log ringkasan fasilitas yang ditemukan
            total_facilities = sum(len(places) for places in detailed_facilities.values())
            logger.info(f"Found {total_facilities} detailed facilities for {outlet['Nama Outlet']}")
            
        except Exception as e:
            logger.error(f"Error processing detailed facilities for outlet {outlet.get('Nama Outlet', 'Unknown')}: {e}")
            # Tetap tambahkan outlet tanpa detail fasilitas
            enhanced_outlet = outlet.copy()
            enhanced_outlet['detailed_facilities'] = {}
            enhanced_results.append(enhanced_outlet)
    
    logger.info(f"Completed processing detailed facilities for {len(enhanced_results)} outlets")
    return enhanced_results
def get_nearby_places_detail(lat, lon, category, radius=100):
    """
    Mendapatkan detail fasilitas di sekitar koordinat berdasarkan kategori
    
    Parameters:
    lat (float): Koordinat latitude
    lon (float): Koordinat longitude
    category (str): Kategori fasilitas
    radius (int): Radius pencarian dalam meter
    
    Returns:
    list: Daftar fasilitas dengan detail
    """
    # Cek apakah hasil sudah ada di cache
    cache_key = f"detail_{lat},{lon},{category},{radius}"
    if ENABLE_CACHE and cache_key in api_cache:
        logger.info(f"Using cached detail result for {cache_key}")
        return api_cache[cache_key]
    
    # Kategori yang akan diperiksa dengan tag yang relevan
    category_queries = get_simplified_queries() if USE_SIMPLIFIED_QUERIES else get_comprehensive_queries()
    
    # Format query dengan koordinat dan radius
    query = category_queries.get(category, "").format(radius=radius, lat=lat, lon=lon)
    
    places = []
    
    # Panggil API
    data = call_overpass_api(query)
    
    if data:
        elements = data.get("elements", [])
        
        # Proses elemen untuk mendapatkan detail
        for element in elements:
            tags = element.get("tags", {})
            name = tags.get("name", "")
            
            # Periksa apakah elemen ini termasuk dalam kategori yang dicari
            element_categories = analyze_element_for_categories(tags, name)
            
            if element_categories[category]:
                # Tentukan tipe tempat berdasarkan tag
                place_type = "Unknown"
                
                # Kategori yang sudah ada
                if category == 'residential':
                    if tags.get("building") in ["apartments", "dormitory"]:
                        place_type = "Apartment/Dormitory"
                    elif tags.get("building") == "house":
                        place_type = "House"
                    elif "cluster" in name.lower() or "villa" in name.lower():
                        place_type = "Cluster/Villa"
                    elif "perumahan" in name.lower():
                        place_type = "Housing Complex"
                    else:
                        place_type = "Residential Area"
                        
                elif category == 'education':
                    if "university" in tags.get("amenity", "") or "universitas" in name.lower():
                        place_type = "University"
                    elif "school" in tags.get("amenity", "") or any(x in name.lower() for x in ["sd", "smp", "sma", "smk", "sekolah"]):
                        place_type = "School"
                    elif "kindergarten" in tags.get("amenity", "") or any(x in name.lower() for x in ["tk", "paud"]):
                        place_type = "Kindergarten"
                    elif "pesantren" in name.lower():
                        place_type = "Islamic Boarding School"
                    elif "kursus" in name.lower() or "course" in name.lower() or "training" in name.lower():
                        place_type = "Course/Training Center"
                    else:
                        place_type = "Educational Institution"
                        
                elif category == 'public_area':
                    if "hospital" in tags.get("amenity", "") or "rumah sakit" in name.lower() or "rs" in name.lower():
                        place_type = "Hospital"
                    elif "clinic" in tags.get("amenity", "") or "klinik" in name.lower() or "puskesmas" in name.lower():
                        place_type = "Clinic"
                    elif "park" in tags.get("leisure", "") or "taman" in name.lower():
                        place_type = "Park"
                    elif "place_of_worship" in tags.get("amenity", "") or any(x in name.lower() for x in ["masjid", "gereja", "pura", "vihara", "klenteng"]):
                        place_type = "Place of Worship"
                    elif "museum" in tags.get("tourism", "") or "museum" in name.lower():
                        place_type = "Museum"
                    elif "bus_station" in tags.get("amenity", "") or "terminal" in name.lower():
                        place_type = "Bus Station/Terminal"
                    elif "station" in tags.get("public_transport", "") or "stasiun" in name.lower():
                        place_type = "Train/Metro Station"
                    elif "terminal" in tags.get("aeroway", "") or "bandara" in name.lower() or "airport" in name.lower():
                        place_type = "Airport"
                    else:
                        place_type = "Public Facility"
                
                elif category == 'culinary':
                    if "restaurant" in tags.get("amenity", "") or "restoran" in name.lower():
                        place_type = "Restaurant"
                    elif "cafe" in tags.get("amenity", "") or "cafe" in name.lower() or "kafe" in name.lower():
                        place_type = "Cafe"
                    elif "food_court" in tags.get("amenity", "") or "food court" in name.lower():
                        place_type = "Food Court"
                    elif "fast_food" in tags.get("amenity", "") or "fast food" in name.lower():
                        place_type = "Fast Food"
                    elif "warmindo" in name.lower():
                        place_type = "Warmindo"
                    elif "warung" in name.lower() or "warteg" in name.lower():
                        place_type = "Warung"
                    elif "kedai" in name.lower():
                        place_type = "Kedai"
                    elif "bakery" in tags.get("shop", "") or "bakery" in name.lower() or "roti" in name.lower():
                        place_type = "Bakery"
                    elif "coffee" in tags.get("shop", "") or "kopi" in name.lower():
                        place_type = "Coffee Shop"
                    elif any(x in name.lower() for x in ["ayam", "chicken", "bakso", "mie", "nasi", "soto", "pecel"]):
                        place_type = "Food Stall"
                    else:
                        place_type = "Food & Beverage"
                        
                elif category == 'business_center':
                    if "office" in tags.get("building", "") or "perkantoran" in name.lower():
                        place_type = "Office Building"
                    elif "ruko" in name.lower():
                        place_type = "Shophouse"
                    elif "coworking" in name.lower():
                        place_type = "Coworking Space"
                    elif "industrial" in tags.get("landuse", "") or "kawasan industri" in name.lower():
                        place_type = "Industrial Area"
                    elif "supermarket" in tags.get("shop", "") or "supermarket" in name.lower():
                        place_type = "Supermarket"
                    elif "mall" in tags.get("shop", "") or "mall" in name.lower() or "plaza" in name.lower():
                        place_type = "Shopping Mall"
                    elif "marketplace" in tags.get("amenity", "") or "pasar" in name.lower() or "market" in name.lower():
                        place_type = "Market"
                    elif "convenience" in tags.get("shop", "") or "alfamart" in name.lower() or "indomaret" in name.lower():
                        place_type = "Convenience Store"
                    elif "shop" in tags:
                        place_type = "Shop"
                    else:
                        place_type = "Commercial Area"
                
                # Kategori baru
                elif category == 'groceries':
                    if "supermarket" in tags.get("shop", "") or "supermarket" in name.lower():
                        place_type = "Supermarket"
                    elif "grocery" in tags.get("shop", "") or "grocery" in name.lower() or "sembako" in name.lower():
                        place_type = "Grocery Store"
                    elif "greengrocer" in tags.get("shop", "") or "sayur" in name.lower() or "buah" in name.lower():
                        place_type = "Greengrocer/Fruit Shop"
                    elif "butcher" in tags.get("shop", "") or "daging" in name.lower() or "meat" in name.lower():
                        place_type = "Butcher Shop"
                    elif "seafood" in tags.get("shop", "") or "seafood" in name.lower():
                        place_type = "Seafood Shop"
                    elif "marketplace" in tags.get("amenity", "") or "pasar" in name.lower() or "market" in name.lower():
                        place_type = "Traditional Market"
                    elif "bakery" in tags.get("shop", "") or "bakery" in name.lower() or "roti" in name.lower():
                        place_type = "Bakery"
                    elif "kelontong" in name.lower():
                        place_type = "Small Grocery"
                    else:
                        place_type = "Grocery Store"
                
                elif category == 'convenient_stores':
                    if "indomaret" in name.lower():
                        place_type = "Indomaret"
                    elif "alfamart" in name.lower() or "alfamidi" in name.lower() or "alfa" in name.lower():
                        place_type = "Alfamart/Alfamidi"
                    elif "circle k" in name.lower():
                        place_type = "Circle K"
                    elif "family mart" in name.lower():
                        place_type = "Family Mart"
                    elif "lawson" in name.lower():
                        place_type = "Lawson"
                    elif "7-eleven" in name.lower() or "7 eleven" in name.lower() or "seven eleven" in name.lower():
                        place_type = "7-Eleven"
                    elif "minimart" in name.lower() or "mini mart" in name.lower() or "mini market" in name.lower():
                        place_type = "Mini Market"
                    elif "convenience" in tags.get("shop", "") or "convenience" in name.lower():
                        place_type = "Convenience Store"
                    elif "kiosk" in tags.get("shop", "") or "kios" in name.lower() or "warung" in name.lower():
                        place_type = "Kiosk/Small Shop"
                    else:
                        place_type = "Convenience Store"
                
                elif category == 'industrial':
                    if "factory" in tags.get("building", "") or "pabrik" in name.lower() or "factory" in name.lower():
                        place_type = "Factory"
                    elif "warehouse" in tags.get("building", "") or "gudang" in name.lower() or "warehouse" in name.lower():
                        place_type = "Warehouse"
                    elif "industrial" in tags.get("landuse", "") or "kawasan industri" in name.lower() or "industrial" in name.lower():
                        place_type = "Industrial Area"
                    elif "workshop" in tags.get("industrial", "") or "bengkel" in name.lower() or "workshop" in name.lower():
                        place_type = "Workshop"
                    elif "manufacturing" in tags.get("building", "") or "manufacturing" in name.lower() or "manufaktur" in name.lower():
                        place_type = "Manufacturing Facility"
                    else:
                        place_type = "Industrial Facility"
                
                elif category == 'hospital_clinic':
                    if "hospital" in tags.get("amenity", "") or "rumah sakit" in name.lower() or "hospital" in name.lower() or "rs" in name.lower():
                        place_type = "Hospital"
                    elif "clinic" in tags.get("amenity", "") or "klinik" in name.lower() or "clinic" in name.lower():
                        place_type = "Clinic"
                    elif "doctors" in tags.get("amenity", "") or "dokter" in name.lower() or "doctor" in name.lower():
                        place_type = "Doctor's Office"
                    elif "pharmacy" in tags.get("amenity", "") or "apotek" in name.lower() or "apotik" in name.lower() or "pharmacy" in name.lower():
                        place_type = "Pharmacy"
                    elif "dentist" in tags.get("amenity", "") or "gigi" in name.lower() or "dental" in name.lower():
                        place_type = "Dental Clinic"
                    elif "puskesmas" in name.lower() or "health center" in name.lower() or "health centre" in name.lower():
                        place_type = "Community Health Center"
                    elif "laboratory" in name.lower() or "lab" in name.lower() or "laboratorium" in name.lower():
                        place_type = "Medical Laboratory"
                    else:
                        place_type = "Healthcare Facility"
                
                # Ambil koordinat elemen
                elem_lat = element.get("lat")
                elem_lon = element.get("lon")
                
                # Jika node tidak memiliki koordinat, coba cari di koordinat center untuk way
                if elem_lat is None and elem_lon is None and element.get("type") == "way":
                    # Untuk way, OpenStreetMap tidak memberikan koordinat langsung
                    # Gunakan center dari bounding box sebagai estimasi
                    bounds = element.get("bounds", {})
                    if bounds:
                        elem_lat = (bounds.get("minlat", 0) + bounds.get("maxlat", 0)) / 2
                        elem_lon = (bounds.get("minlon", 0) + bounds.get("maxlon", 0)) / 2
                
                # Tambahkan ke daftar tempat
                places.append({
                    "name": name if name else "Unnamed",
                    "type": place_type,
                    "lat": elem_lat,
                    "lon": elem_lon,
                    "tags": tags
                })
    
    # Simpan ke cache
    if ENABLE_CACHE:
        api_cache[cache_key] = places.copy()
        # Simpan cache ke file secara periodik
        if len(api_cache) % 10 == 0:
            save_cache()
    
    return places

# Inisialisasi cache saat modul di-load
load_cache()