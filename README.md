# Agentic CRM — Kampanya Denetim Sistemi

Kampanyaların metin, görsel ve hukuki uygunluğunu yapay zeka destekli çoklu ajan mimarisiyle denetleyen bir Streamlit uygulamasıdır.

---

## İçindekiler

- [Özellikler](#özellikler)
- [Proje Yapısı](#proje-yapısı)
- [Kurulum](#kurulum)
- [Ortam Değişkenleri](#ortam-değişkenleri)
- [Uygulamayı Çalıştırma](#uygulamayı-çalıştırma)
- [Kullanım](#kullanım)
- [Desteklenen Modeller](#desteklenen-modeller)
- [Kullanıcı Yönetimi](#kullanıcı-yönetimi)
- [Testler](#testler)
- [Teknoloji Yığını](#teknoloji-yığını)
- [Görseller](#görseller)

---

## Özellikler

| Modül | Açıklama |
|---|---|
| **Metin Denetimi** | Kampanya metnini bankacılık mevzuatına göre denetler; uygun / düzenlenmeli / uygunsuz olarak sınıflandırır |
| **Görsel Denetim** | Yüklenen kampanya görselini onaylı metin ile karşılaştırır; OCR, logo ve renk uyumunu kontrol eder |
| **Hukuk & Strateji Denetimi** | Kullanıcının yüklediği PDF/TXT belgelerini veya varsayılan BDDK mevzuatını baz alarak 0–100 uygunluk puanı üretir |
| **Karşılaştırmalı Analiz** | Aynı kampanya metnini birden fazla modelle paralel olarak denetler ve sonuçları karşılaştırır |
| **Denetim Geçmişim** | Kullanıcının son 7 güne ait denetim geçmişini filtreli olarak görüntüler |
| **Mevzuat Rehberi** | Sidebar üzerinden uyum mevzuatı ve hukuki düzenlemelere arama yapılabilir diyalog ile erişim |
| **Yönetim Paneli** | Yalnızca `admin` hesabında görünür; sistem durumu, kullanıcı yönetimi, prompt/mevzuat düzenleme, arama geçmişi ve istatistikleri içerir |
| **Güvenli Giriş** | JWT cookie tabanlı oturum, SHA-256 şifre hash, rate limiting, hesap kilitleme, e-posta ile şifre sıfırlama |
| **Güvenlik Katmanı** | Enjeksiyon tespiti ve zararlı girdi filtreleme |
| **Çoklu Model Desteği** | Anthropic Claude, OpenAI ve DeepSeek modelleri arasında geçiş yapılabilir |

---

## Proje Yapısı

```
AgenticCRM/
│
├── multiagentcrm.py                # Ana giriş noktası: kimlik doğrulama, tema, sekme yönlendirmesi
│
├── agents/                         # LangGraph iş akışı ajanları
│   ├── llm_factory.py              # Birleşik LLM sağlayıcı fabrikası
│   ├── campaigntextagent.py        # Metin uyum denetim ajanı (RAG + Chroma)
│   ├── visualcontrolagent.py       # Görsel denetim ajanı (Vision LLM)
│   ├── legalstrategyagent.py       # Hukuk & strateji denetim ajanı
│   ├── output_parser.py            # LLM çıktı ayrıştırıcı
│   ├── audit_logger.py             # Denetim kaydı (MongoDB)
│   └── security.py                 # Enjeksiyon tespiti ve güvenlik katmanı
│
├── ui/                             # Streamlit sekme UI modülleri
│   ├── tab_metin_denetimi.py       # Tab: Metin Denetimi
│   ├── tab_gorsel_denetim.py       # Tab: Görsel Denetim
│   ├── tab_hukuk_strateji.py       # Tab: Hukuk & Strateji
│   ├── tab_karsilastirma.py        # Tab: Karşılaştırmalı Analiz
│   ├── tab_gecmisim.py             # Tab: Denetim Geçmişim (kullanıcı, 7 gün)
│   ├── tab_sistem_durumu.py        # Admin Tab: Sistem Durumu
│   ├── tab_yonetim_paneli.py       # Admin Tab: Kullanıcı Yönetimi
│   ├── tab_prompt_yonetimi.py      # Admin Tab: Mevzuat & Promptlar
│   ├── tab_gecmis.py               # Admin Tab: Arama Geçmişi
│   ├── tab_istatistik.py           # Admin Tab: Arama İstatistikleri
│   ├── error_handler.py            # Merkezi hata yönetimi
│   └── assets/
│       └── bank_hero.svg           # Login ekranı SVG görseli
│
├── user/                           # Kullanıcı ve kimlik doğrulama modülleri
│   ├── db.py                       # MongoDB kullanıcı CRUD işlemleri
│   ├── mongo.py                    # MongoDB bağlantı yöneticisi
│   ├── jwt_auth.py                 # JWT oluşturma ve doğrulama
│   ├── rate_limiter.py             # Giriş denemesi sınırlama ve hesap kilitleme
│   ├── reset_tokens.py             # Şifre sıfırlama token yönetimi
│   ├── mailer.py                   # Şifre sıfırlama e-posta gönderimi
│   └── prompt_store.py             # Prompt ve mevzuat içeriği yönetimi
│
├── state/
│   └── agentstate.py               # Paylaşılan TypedDict durum tanımı
│
├── css/
│   └── main.css                    # ING marka teması
│
├── data/                           # Varsayılan mevzuat dosyaları
│   ├── regulations_compliance.txt
│   └── regulations_legal.txt
│
├── tests/                          # Pytest test sınıfları
│   ├── test_llm_factory.py
│   ├── test_campaigntextagent.py
│   ├── test_visualcontrolagent.py
│   ├── test_legalstrategyagent.py
│   ├── test_output_parser.py
│   ├── test_security.py
│   ├── test_audit_logger.py
│   ├── test_jwt_auth.py
│   ├── test_rate_limiter.py
│   ├── test_db.py
│   └── test_tab_istatistik.py
│
├── .env                            # API anahtarları (.gitignore'da)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Kurulum

### Gereksinimler

- Python 3.10+
- pip
- MongoDB (yerel veya Atlas)

### Adımlar

```bash
# 1. Repoyu klonlayın
git clone https://github.com/mehmetalikoker/MultiAgentCRM
cd AgenticCRM

# 2. Sanal ortam oluşturun ve aktif edin
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Bağımlılıkları yükleyin
pip install -r requirements.txt
```

---

## Ortam Değişkenleri

Proje kök dizininde bir `.env` dosyası oluşturun:

```env
# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
OPENAI_API_KEY=sk-...

# DeepSeek
DEEPSEEK_API_KEY=...

# MongoDB
MONGO_URI=mongodb+srv://...

# JWT
JWT_SECRET=gizli-anahtar-buraya

# E-posta (şifre sıfırlama)
MAIL_HOST=smtp.sirket.com
MAIL_PORT=587
MAIL_USER=noreply@sirket.com
MAIL_PASS=...

# LangSmith (opsiyonel — izleme)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=AgenticCRM
```

> `.env` dosyası `.gitignore`'a eklenmiştir; asla repoya göndermeyin.

---

## Uygulamayı Çalıştırma

```bash
streamlit run multiagentcrm.py
```

Tarayıcıda `http://localhost:8501` adresini açın.

---

## Kullanım

### Giriş

Uygulama açıldığında login ekranı gelir. İlk admin kullanıcısı MongoDB üzerinden manuel olarak oluşturulur:

```python
import hashlib
pw_hash = hashlib.sha256(b"SIFRENIZ").hexdigest()
# users koleksiyonuna ekleyin:
# { "username": "admin", "password_hash": pw_hash, "display_name": "Yönetici", "role": "admin" }
```

**Şifre Sıfırlama:** Giriş ekranındaki "Şifremi Unuttum" bağlantısı ile kayıtlı e-posta adresine 6 haneli kod gönderilir.

---

### Kullanıcı Sekmeleri

#### Tab 1 — Metin Denetimi

1. Kampanya metnini girin
2. Dağıtım kanalını seçin (SMS, E-posta, Push Bildirimi vb.)
3. **Denetle** butonuna tıklayın

Sistem üç sonuç üretir:

| Sonuç | Açıklama |
|---|---|
| ✅ Uygun | Mevzuata aykırı ifade ve öneri yok |
| ⚠️ Düzenlenmesi gerekiyor | Onaylandı fakat iyileştirme önerileri mevcut |
| ❌ Uygunsuz | Mevzuat ihlali tespit edildi |

#### Tab 2 — Görsel Denetim

1. Kampanya görselini yükleyin (JPG, JPEG, PNG)
2. Daha önce onaylanmış kampanya metnini girin
3. **Görseli Denetle** butonuna tıklayın

> Görsel denetim yalnızca vision destekli modellerle çalışır. DeepSeek bu sekme için kullanılamaz.

#### Tab 3 — Hukuk & Strateji Denetimi

1. İsteğe bağlı olarak PDF veya TXT formatında hukuki belge(ler) yükleyin
2. Denetlenecek kampanya metnini girin
3. **Hukuki Denetim Yap** butonuna tıklayın

Belge yüklenmezse sistem varsayılan BDDK mevzuatını kullanır. Sonuç olarak 0–100 arası bir uygunluk puanı üretilir:

| Puan | Renk | Yorum |
|---|---|---|
| 70–100 | Yeşil | Uygun |
| 40–69 | Turuncu | Dikkat gerektirir |
| 0–39 | Kırmızı | Yüksek risk |

#### Tab 4 — Karşılaştırmalı Analiz

Aynı kampanya metnini birden fazla modelle aynı anda denetler; sonuçları yan yana karşılaştırmanızı sağlar.

#### Tab 5 — Denetim Geçmişim

Son 7 güne ait kişisel denetim kayıtlarını listeler; tarih ve denetim türüne göre filtrelenebilir.

---

### Yönetici Sekmeleri *(yalnızca admin)*

| Sekme | Açıklama |
|---|---|
| 🖥️ Sistem Durumu | MongoDB bağlantı durumu, koleksiyon boyutları, grafik gösterim |
| 👥 Kullanıcı Yönetimi | Kullanıcı ekleme, silme, şifre yönetimi, hesap kilitleme |
| 📝 Mevzuat & Promptlar | Denetim promptlarını ve mevzuat içeriklerini düzenleme |
| 📋 Arama Geçmişi | Tüm kullanıcıların denetim kayıtlarını görüntüleme |
| 📊 Arama İstatistikleri | Denetim türü ve model bazlı kullanım istatistikleri |

---

## Desteklenen Modeller

| Sağlayıcı | Model | Vision |
|---|---|---|
| Anthropic | Claude Opus 4.7 | ✅ |
| Anthropic | Claude Sonnet 4.6 | ✅ |
| Anthropic | Claude Haiku 4.5 | ✅ |
| OpenAI | GPT-4 Turbo | ✅ |
| DeepSeek | DeepSeek Chat | ❌ |

Sidebar'dan aktif model seçilir; seçim tüm denetim adımlarına uygulanır.

---

## Kullanıcı Yönetimi

Kullanıcılar MongoDB `users` koleksiyonunda tutulur. Şifreler SHA-256 ile hashlenerek saklanır.

```json
{
  "username": "admin",
  "password_hash": "<sha256>",
  "display_name": "Yönetici",
  "role": "admin",
  "email": "admin@sirket.com"
}
```

Manuel olarak şifre hash'i üretmek için:

```bash
python -c "import hashlib; print(hashlib.sha256(b'SIFRENIZ').hexdigest())"
```

**Hesap Kilitleme:** Belirli sayıda başarısız giriş denemesinin ardından hesap otomatik olarak kilitlenir; admin panelinden açılabilir.

**Çoklu Cihaz Koruması:** Aynı hesaba başka bir cihazdan giriş yapıldığında önceki oturum sonlandırılır.

---

## Testler

```bash
# Tüm testleri çalıştır
.venv\Scripts\python.exe -m pytest tests/ -v

# Belirli bir modülü test et
.venv\Scripts\python.exe -m pytest tests/test_llm_factory.py -v

# İsme göre filtrele
.venv\Scripts\python.exe -m pytest tests/ -k "score" -v
```

Test kapsamı:

| Dosya | Kapsam |
|---|---|
| `test_llm_factory.py` | Model prefix routing, temperature, fallback |
| `test_campaigntextagent.py` | Compliance checker, mevzuat DB, state şeması |
| `test_visualcontrolagent.py` | encode_image (MIME, base64), visual auditor |
| `test_legalstrategyagent.py` | Score parsing/clamping, fallback/döküman seçimi |
| `test_output_parser.py` | LLM çıktı ayrıştırma ve hata durumları |
| `test_security.py` | Enjeksiyon tespiti, girdi doğrulama |
| `test_audit_logger.py` | Denetim kaydı yazma ve sorgulama |
| `test_jwt_auth.py` | Token oluşturma, doğrulama, süresi dolmuş token |
| `test_rate_limiter.py` | Giriş denemesi sayacı, kilitleme mantığı |
| `test_db.py` | MongoDB kullanıcı CRUD işlemleri |
| `test_tab_istatistik.py` | İstatistik sekmesi veri işleme |

---

## Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| UI | Streamlit 1.57 |
| Ajan Orkestrasyonu | LangGraph 1.1 |
| LLM Entegrasyonu | LangChain (Anthropic, OpenAI, DeepSeek) |
| Vektör Veritabanı | ChromaDB 1.5 |
| Embedding | OpenAI Embeddings |
| Veritabanı | MongoDB (Atlas veya yerel) |
| PDF İşleme | PyPDFLoader (LangChain Community) |
| Görsel İşleme | Pillow 12 |
| Kimlik Doğrulama | JWT + SHA-256 + Cookie |
| E-posta | SMTP (şifre sıfırlama) |
| Test | pytest 9 |

---

## Görseller

<img width="1025" height="510" alt="Ekran görüntüsü 2026-05-17 152804" src="https://github.com/user-attachments/assets/f1ef81d3-4c37-4e06-9934-81cb463411c5" />

<img width="1888" height="424" alt="Ekran görüntüsü 2026-05-17 152420" src="https://github.com/user-attachments/assets/fa0ea0f6-a7f6-4ce4-8b45-5a481aa5fd8f" />
