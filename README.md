# Agentic CRM — Kampanya Denetim Sistemi

ING Bank kampanyalarının metin, görsel ve hukuki uygunluğunu yapay zeka destekli çoklu ajan mimarisiyle denetleyen bir Streamlit uygulamasıdır.

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

---

## Özellikler

| Modül | Açıklama |
|---|---|
| **Metin Denetimi** | Kampanya metnini bankacılık mevzuatına göre denetler; uygun / düzenlenmeli / uygunsuz olarak sınıflandırır |
| **Görsel Denetim** | Yüklenen kampanya görselini onaylı metin ile karşılaştırır; OCR, logo ve renk uyumunu kontrol eder |
| **Hukuk & Strateji Denetimi** | Kullanıcının yüklediği PDF/TXT belgelerini veya varsayılan BDDK mevzuatını baz alarak 0–100 uygunluk puanı üretir |
| **Yönetim Paneli** | Yalnızca `admin` hesabında görünür; yeni kullanıcı ekleme ve silme işlemleri yapılabilir |
| **Çoklu Model Desteği** | OpenAI, Anthropic Claude, Google Gemini ve DeepSeek modelleri arasında geçiş yapılabilir |
| **Güvenli Giriş** | SHA-256 ile hashlenmiş şifreler, JSON tabanlı kullanıcı yönetimi |

---

## Proje Yapısı

```
AgenticCRM/
│
├── multiagentcrm.py            # Ana giriş noktası: kimlik doğrulama, tema, sekme yönlendirmesi
│
├── agents/                     # LangGraph iş akışı ajanları
│   ├── llm_factory.py          # Birleşik LLM sağlayıcı fabrikası
│   ├── campaigntextagent.py    # Metin uyum denetim ajanı (RAG + Chroma)
│   ├── visualcontrolagent.py   # Görsel denetim ajanı (Vision LLM)
│   └── legalstrategyagent.py   # Hukuk & strateji denetim ajanı
│
├── ui/                         # Streamlit sekme UI modülleri
│   ├── tab_metin_denetimi.py   # Tab 1: Metin Denetimi
│   ├── tab_gorsel_denetim.py   # Tab 2: Görsel Denetim
│   ├── tab_hukuk_strateji.py   # Tab 3: Hukuk & Strateji
│   └── tab_yonetim_paneli.py   # Tab 4: Yönetim Paneli (yalnızca admin)
│
├── state/
│   └── agentstate.py           # Paylaşılan TypedDict durum tanımı
│
├── user/                       # Kullanıcı veritabanı (.gitignore'da)
│   └── users.json
│
├── tests/                      # Pytest test sınıfları
│   ├── test_llm_factory.py
│   ├── test_campaigntextagent.py
│   ├── test_visualcontrolagent.py
│   └── test_legalstrategyagent.py
│
├── .env                        # API anahtarları (.gitignore'da)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Kurulum

### Gereksinimler

- Python 3.10+
- pip

### Adımlar

```bash
# 1. Repoyu klonlayın
git clone <repo-url>
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
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
GEMINI_API_KEY=AIza...

# DeepSeek
DEEPSEEK_API_KEY=...

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

Uygulama açıldığında login ekranı gelir. Varsayılan admin hesabı:

| Alan | Değer |
|---|---|
| Kullanıcı Adı | `admin` |
| Şifre | `admin123` |

> İlk girişten sonra admin şifresini **Yönetim Paneli** üzerinden değiştirmeniz önerilir.

### Tab 1 — Metin Denetimi

1. Kampanya metnini girin
2. Dağıtım kanalını seçin (SMS, E-posta, Push Bildirimi vb.)
3. **Denetle** butonuna tıklayın

Sistem üç sonuç üretir:

| Sonuç | Açıklama |
|---|---|
| ✅ Uygun | Mevzuata aykırı ifade ve öneri yok |
| ⚠️ Düzenlenmesi gerekiyor | Onaylandı fakat iyileştirme önerileri mevcut |
| ❌ Uygunsuz | Mevzuat ihlali tespit edildi |

### Tab 2 — Görsel Denetim

1. Kampanya görselini yükleyin (JPG, JPEG, PNG)
2. Daha önce onaylanmış kampanya metnini girin
3. **Görseli Denetle** butonuna tıklayın

> Görsel denetim yalnızca vision destekli modellerle çalışır. GPT-3.5 Turbo ve DeepSeek bu sekme için kullanılamaz.

### Tab 3 — Hukuk & Strateji Denetimi

1. İsteğe bağlı olarak PDF veya TXT formatında hukuki belge(ler) yükleyin
2. Denetlenecek kampanya metnini girin
3. **Hukuki Denetim Yap** butonuna tıklayın

Belge yüklenmezse sistem varsayılan BDDK mevzuatını kullanır. Sonuç olarak 0–100 arası bir uygunluk puanı üretilir:

| Puan | Renk | Yorum |
|---|---|---|
| 70–100 | Yeşil | Uygun |
| 40–69 | Turuncu | Dikkat gerektirir |
| 0–39 | Kırmızı | Yüksek risk |

### Tab 4 — Yönetim Paneli *(yalnızca admin)*

- Mevcut kullanıcıları listeler
- Yeni kullanıcı ekler (kullanıcı adı, şifre, görünen ad)
- Kullanıcı siler (`admin` silinemez)

---

## Desteklenen Modeller

| Sağlayıcı | Model | Vision |
|---|---|---|
| Anthropic | Claude Opus 4.7 | ✅ |
| Anthropic | Claude Sonnet 4.6 | ✅ |
| Anthropic | Claude Haiku 4.5 | ✅ |
| OpenAI | GPT-4 Turbo | ✅ |
| Google | Gemini 2.0 Flash | ✅ |
| Google | Gemini 2.0 Flash Lite | ✅ |
| Google | Gemini 1.5 Pro | ✅ |
| DeepSeek | DeepSeek Chat | ❌ |

Sidebar'dan aktif model seçilir; seçim tüm denetim adımlarına uygulanır.

---

## Kullanıcı Yönetimi

Kullanıcılar `user/users.json` dosyasında tutulur. Şifreler SHA-256 ile hashlenerek saklanır.

```json
{
  "users": [
    {
      "username": "admin",
      "password_hash": "<sha256>",
      "display_name": "Yönetici"
    }
  ]
}
```

Manuel olarak şifre hash'i üretmek için:

```bash
python -c "import hashlib; print(hashlib.sha256(b'SIFRENIZ').hexdigest())"
```

> `user/` klasörü `.gitignore`'a eklenmiştir; kullanıcı bilgileri repoya gitmez.

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

| Dosya | Test Sayısı | Kapsam |
|---|---|---|
| `test_llm_factory.py` | 11 | Model prefix routing, temperature, fallback |
| `test_campaigntextagent.py` | 9 | Compliance checker, mevzuat DB, state şeması |
| `test_visualcontrolagent.py` | 13 | encode_image (MIME, base64), visual auditor |
| `test_legalstrategyagent.py` | 16 | Score parsing/clamping, fallback/döküman seçimi |

---

## Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| UI | Streamlit 1.57 |
| Ajan Orkestrasyonu | LangGraph 1.1 |
| LLM Entegrasyonu | LangChain (OpenAI, Anthropic, Google, DeepSeek) |
| Vektör Veritabanı | ChromaDB 1.5 |
| Embedding | OpenAI Embeddings |
| PDF İşleme | PyPDFLoader (LangChain Community) |
| Görsel İşleme | Pillow 12 |
| Kimlik Doğrulama | SHA-256 + JSON |
| Test | pytest 9 |
