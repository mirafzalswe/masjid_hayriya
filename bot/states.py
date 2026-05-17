from aiogram.fsm.state import State, StatesGroup


class MurojaatState(StatesGroup):
    """Murojaat yuborish bosqichlari"""
    fio = State()
    telefon = State()
    muhtojlik_turi = State()
    mazmun = State()
    priority = State()
    tasdiqlash = State()


class SearchState(StatesGroup):
    """Shaxs qidirish bosqichlari"""
    query = State()


class YordamState(StatesGroup):
    """Shaxsga yordam qo'shish bosqichlari"""
    qidiruv        = State()
    shaxs_tanlash  = State()
    turi           = State()
    miqdor         = State()   # faqat 'pul' uchun
    mazmun         = State()   # 'pul'dan tashqari turlarda
    bergan_fio     = State()
    bergan_telefon = State()
    tasdiqlash     = State()
