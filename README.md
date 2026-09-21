# Timed & View-Once Media Saver for Telegram (Saveit)

Bu skript Telegram akkauntingizga kelgan har qanday bir martalik (view-once / self-destructing / timed) rasm, video, ovozli xabar (voice note) va yumaloq videolarni (video note) Telegram serveridan o'chib ketmasidan oldin avtomatik ravishda yuklab olib, **Saqlangan xabarlar ("Saved Messages")** ga doimiy (o'chib ketmaydigan) qilib yuboradi.

## Imkoniyatlar

* ✅ **Avtomatik bir martalik mediani saqlash**: Akkauntingizga bir martalik rasm, video yoki ovozli xabar kelishi bilan uni avtomatik saqlaydi.
* ✅ **Doimiy format**: Rasm va videolarni buzilmagan, asl ko'rinishida va doimiy saqlaydi.
* ✅ **To'liq ma'lumot (Caption)**: Yuboruvchining ismi, username, ID raqami, xabar yuborilgan vaqt va xabarga biriktirilgan asl matn (izoh) Saqlangan xabarlarda ko'rsatiladi.
* ✅ **Qo'lda saqlash (`.saveit`)**: Oddiy media xabarlarga javob (`reply`) tariqasida `.saveit` yozsangiz ham ularni Saqlangan xabarlarga nusxalab beradi.
* ✅ **Ovozli va yumaloq videolar**: Ovozli xabarlar va doirasimon (yumaloq) videolarni to'g'ri ijro etiladigan shaklda saqlaydi.

---

## Sozlamalar (`.env`)

`.env` faylida quyidagi parametrlarni sozlashingiz mumkin:

```ini
API_ID=YOUR_API_ID
API_HASH=YOUR_API_HASH
HANDLER=.saveit          # Qo'lda saqlash prefiksi
AUTO_SAVE_TIMED=true     # Bir martalik medialarni avtomatik saqlash (true/false)
FORCE_DOCUMENT=false     # true = barchasini hujjat/fayl qilib yuborish, false = rasm/videoni to'g'ridan-to'g'ri ochiladigan qilish
```

---

## O'rnatish va Ishga tushirish

1. **Kutubxonalarni o'rnatish**:
```bash
pip install telethon python-dotenv
```

2. **Ishga tushirish**:
```bash
./run.sh
```
yoki to'g'ridan-to'g'ri:
```bash
python3 Saveit.py
```

> **Eslatma**: Birinchi marta ishga tushirganda Telegram telefon raqamingiz va tasdiqlash kodini kiritishingiz so'raladi. Shundan so'ng sessiya `save.session` faylida saqlanib qoladi va keyingi safar qayta kod so'ramaydi.
