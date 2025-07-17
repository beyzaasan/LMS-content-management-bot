import requests
import json
from getpass import getpass

def get_moodle_info():
    """Helper script to get Moodle token and user ID"""
    
    print("=== Moodle Bilgilerini Alma ===")
    
    # Moodle site URL'si
    moodle_url = input("Moodle site URL'nizi girin (örn: https://moodle.example.com): ").strip()
    if not moodle_url.endswith('/'):
        moodle_url += '/'
    
    # Kullanıcı bilgileri
    username = input("Moodle kullanıcı adınızı girin: ")
    password = getpass("Moodle şifrenizi girin: ")
    
    try:
        # 1. Önce giriş yapalım
        session = requests.Session()
        
        # Login sayfasını al
        login_url = f"{moodle_url}login/index.php"
        response = session.get(login_url)
        
        if response.status_code != 200:
            print("❌ Moodle sitesine erişilemiyor!")
            return
        
        # 2. User ID'yi bulmak için profil sayfasına git
        profile_url = f"{moodle_url}user/profile.php"
        profile_response = session.get(profile_url)
        
        if profile_response.status_code == 200:
            # URL'den user ID'yi çıkar
            if 'id=' in profile_response.url:
                user_id = profile_response.url.split('id=')[1].split('&')[0]
                print(f"✅ Moodle User ID: {user_id}")
            else:
                print("⚠️ User ID otomatik bulunamadı, manuel olarak kontrol edin")
                user_id = input("Moodle User ID'nizi manuel olarak girin: ")
        else:
            print("⚠️ Profil sayfasına erişilemedi")
            user_id = input("Moodle User ID'nizi manuel olarak girin: ")
        
        # 3. Token alma
        print("\n=== Token Alma ===")
        print("1. Moodle'da tarayıcınızı açın")
        print("2. Giriş yapın")
        print("3. Sağ üst köşedeki isminize tıklayın")
        print("4. 'Preferences' veya 'Ayarlar' seçin")
        print("5. 'Security keys' veya 'Güvenlik anahtarları' bulun")
        print("6. 'Create a new token' veya 'Yeni token oluştur' tıklayın")
        print("7. Token'ı kopyalayın")
        
        token = input("\nToken'ı buraya yapıştırın: ").strip()
        
        if token and user_id:
            print("\n✅ Başarılı! İşte bilgileriniz:")
            print(f"MOODLE_BASE_URL={moodle_url}")
            print(f"MOODLE_TOKEN={token}")
            print(f"MOODLE_USER_ID={user_id}")
            print(f"USER_ID={user_id}")  # Genellikle aynı değer
            
            # .env dosyasına kaydet
            save_to_env = input("\nBu bilgileri .env dosyasına kaydetmek ister misiniz? (y/n): ")
            if save_to_env.lower() == 'y':
                with open('.env', 'a') as f:
                    f.write(f"\nMOODLE_BASE_URL={moodle_url}")
                    f.write(f"\nMOODLE_TOKEN={token}")
                    f.write(f"\nMOODLE_USER_ID={user_id}")
                    f.write(f"\nUSER_ID={user_id}")
                print("✅ .env dosyasına kaydedildi!")
        
    except Exception as e:
        print(f"❌ Hata oluştu: {str(e)}")

if __name__ == "__main__":
    get_moodle_info() 