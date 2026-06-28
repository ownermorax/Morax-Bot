import os
import re
import time
import logging

logger = logging.getLogger(__name__)


class PersonDatabase:
    def __init__(self, filename):
        self.filename = filename
        self.people = []
        self.search_cache = {}
        self.cache_ttl = 300
        self.last_cache_clean = time.time()
        self.load_database()

    def load_database(self):
        try:
            if not os.path.exists(self.filename):
                logger.error(f"❌ Файл {self.filename} не найден!")
                return

            with open(self.filename, 'r', encoding='utf-8') as f:
                content = f.read()

            self.people = []
            records = re.split(r'\n\[\+\] ', content)

            for record in records:
                if not record.strip():
                    continue
                if not record.startswith('[+]'):
                    record = '[+] ' + record
                person = self.parse_person(record)
                if person:
                    self.people.append(person)

            self.search_cache = {}
            logger.info(f"📚 Загружено {len(self.people)} записей из базы данных")
        except Exception as e:
            logger.error(f"Ошибка загрузки базы данных: {e}")

    def parse_person(self, text):
        try:
            person = {
                'full_info': text.strip(),
                'name': '',
                'phones': [],
                'passports': [],
                'addresses': [],
                'emails': [],
                'telegrams': [],
                'telegram_ids': [],
                'birth_dates': [],
                'snils': [],
                'oms': [],
                'birth_certificates': [],
                'cars': [],
                'inn': [],
                'disability': False,
                'relatives': [],
                'other': []
            }

            lines = text.split('\n')

            for line in lines:
                if line.startswith('[+]'):
                    person['name'] = line.replace('[+]', '').strip()
                    break

            for line in lines:
                line = line.strip()

                relative_match = re.match(
                    r'^(Мать|Отец|Брат|Сестра|Сын|Дочь|Жена|Муж|Бабушка|Дедушка|Внук|Внучка|Тетя|Дядя|Племянник|Племянница):\s*(.+)$',
                    line, re.IGNORECASE
                )
                if relative_match:
                    relation_type = relative_match.group(1).capitalize()
                    relative_info = relative_match.group(2).strip()
                    relative_data = {
                        'relation': relation_type,
                        'full_text': relative_info
                    }
                    date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', relative_info)
                    if date_match:
                        relative_data['birth_date'] = date_match.group(1)
                        name_part = relative_info.replace(date_match.group(1), '').strip().rstrip('-').strip()
                        if name_part:
                            relative_data['name'] = name_part
                    else:
                        relative_data['name'] = relative_info
                    person['relatives'].append(relative_data)
                    continue

                if '•Дата рождения:' in line or '•День рождения:' in line:
                    value = line.split(':', 1)[1].strip() if ':' in line else ''
                    if value:
                        person['birth_dates'].append(value)
                elif '•Телефон:' in line or '•Номер телефона:' in line:
                    phones = line.split(':', 1)[1].strip() if ':' in line else ''
                    if phones:
                        for phone in phones.split('/'):
                            phone = phone.strip()
                            if phone and phone not in person['phones']:
                                person['phones'].append(phone)
                elif '•Паспорт:' in line:
                    value = line.split(':', 1)[1].strip() if ':' in line else ''
                    if value and value not in person['passports']:
                        person['passports'].append(value)
                elif '•Адрес:' in line or '•Адрес 2:' in line:
                    value = line.split(':', 1)[1].strip() if ':' in line else ''
                    if value and value not in person['addresses']:
                        person['addresses'].append(value)
                elif '•Email:' in line:
                    value = line.split(':', 1)[1].strip() if ':' in line else ''
                    if value and value not in person['emails']:
                        person['emails'].append(value)
                elif '•Telegram:' in line:
                    value = line.split(':', 1)[1].strip() if ':' in line else ''
                    if value:
                        if '| id:' in value:
                            parts = value.split('|')
                            tg_part = parts[0].strip()
                            id_part = parts[1].replace('id:', '').strip()
                            if tg_part and tg_part != 'https://t.me/' and tg_part not in person['telegrams']:
                                person['telegrams'].append(tg_part)
                            if id_part and id_part not in person['telegram_ids']:
                                person['telegram_ids'].append(id_part)
                        else:
                            if value and value != 'https://t.me/' and value not in person['telegrams']:
                                person['telegrams'].append(value)
                elif '•СНИЛС:' in line:
                    value = line.split(':', 1)[1].strip() if ':' in line else ''
                    if value and value not in person['snils']:
                        person['snils'].append(value)
                elif '•Полис ОМС:' in line:
                    value = line.split(':', 1)[1].strip() if ':' in line else ''
                    if value and value not in person['oms']:
                        person['oms'].append(value)
                elif '•Транспортное средство:' in line or '•Автомобиль:' in line:
                    value = line.split(':', 1)[1].strip() if ':' in line else ''
                    if value and value not in person['cars']:
                        person['cars'].append(value)
                elif '•ИНН:' in line:
                    value = line.split(':', 1)[1].strip() if ':' in line else ''
                    if value and value not in person['inn']:
                        person['inn'].append(value)
                elif '•Инвалидность:' in line:
                    value = line.split(':', 1)[1].strip() if ':' in line else ''
                    if 'да' in value.lower():
                        person['disability'] = True
                elif '•' in line and ':' in line:
                    key = line.split('•')[1].split(':')[0].strip() if '•' in line else ''
                    value = line.split(':', 1)[1].strip() if ':' in line else ''
                    if key and value:
                        person['other'].append(f"{key}: {value}")

            return person
        except Exception as e:
            logger.error(f"Ошибка парсинга записи: {e}")
            return None

    def search(self, query):
        if not query or len(query) < 2:
            return []

        query = query.lower().strip()
        cache_key = f"{query}"
        if cache_key in self.search_cache:
            cache_time, cache_result = self.search_cache[cache_key]
            if time.time() - cache_time < self.cache_ttl:
                return cache_result

        results = []
        for person in self.people:
            score = 0
            match_reason = []

            if query in person['name'].lower():
                score += 10
                match_reason.append("имя")

            for phone in person['phones']:
                if query in phone.lower():
                    score += 10
                    match_reason.append("телефон")
                    break

            for tg_id in person['telegram_ids']:
                if query in tg_id.lower():
                    score += 10
                    match_reason.append("telegram id")
                    break

            for tg in person['telegrams']:
                if query in tg.lower():
                    score += 10
                    match_reason.append("telegram")
                    break

            for email in person['emails']:
                if query in email.lower():
                    score += 10
                    match_reason.append("email")
                    break

            for passport in person['passports']:
                if query in passport.lower():
                    score += 8
                    match_reason.append("паспорт")
                    break

            for snils in person['snils']:
                if query in snils.lower():
                    score += 8
                    match_reason.append("снилс")
                    break

            for addr in person['addresses']:
                if query in addr.lower():
                    score += 5
                    match_reason.append("адрес")
                    break

            if score > 0:
                results.append({
                    'person': person,
                    'score': score,
                    'reason': ', '.join(match_reason[:3])
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        results = results[:20]
        self.search_cache[cache_key] = (time.time(), results)
        return results

    def format_person_info(self, person):
        lines = []
        lines.append(f"**{person['name']}**")
        lines.append("")

        if person['birth_dates']:
            lines.append(f"**📅 Дата рождения:** {person['birth_dates'][0]}")
        if person['phones']:
            phones = ', '.join(person['phones'])
            lines.append(f"**📞 Телефон:** {phones}")
        if person['emails']:
            emails = ', '.join(person['emails'])
            lines.append(f"**📧 Email:** {emails}")
        if person['telegrams']:
            tgs = []
            for tg in person['telegrams']:
                if tg.startswith('https://t.me/'):
                    tgs.append(f"[{tg.replace('https://t.me/', '@')}]({tg})")
                elif tg.startswith('@'):
                    tgs.append(f"[{tg}](https://t.me/{tg.replace('@', '')})")
                else:
                    tgs.append(tg)
            lines.append(f"**📱 Telegram:** {', '.join(tgs)}")
        if person['telegram_ids']:
            ids = ', '.join([f'`{tid}`' for tid in person['telegram_ids']])
            lines.append(f"**🆔 Telegram ID:** {ids}")
        if person['passports']:
            passports = ', '.join([f'`{p}`' for p in person['passports']])
            lines.append(f"**🪪 Паспорт:** {passports}")
        if person['addresses']:
            for i, addr in enumerate(person['addresses'], 1):
                lines.append(f"**🏠 Адрес{f' {i}' if len(person['addresses']) > 1 else ''}:** {addr}")
        if person['snils']:
            snils = ', '.join([f'`{s}`' for s in person['snils']])
            lines.append(f"**📄 СНИЛС:** {snils}")
        if person['oms']:
            oms = ', '.join([f'`{o}`' for o in person['oms']])
            lines.append(f"**🏥 Полис ОМС:** {oms}")
        if person['birth_certificates']:
            certs = ', '.join([f'`{c}`' for c in person['birth_certificates']])
            lines.append(f"**📜 Свид. о рождении:** {certs}")
        if person['cars']:
            cars = ', '.join(person['cars'])
            lines.append(f"**🚗 Транспорт:** {cars}")
        if person['inn']:
            inns = ', '.join([f'`{i}`' for i in person['inn']])
            lines.append(f"**🔢 ИНН:** {inns}")
        if person['disability']:
            lines.append("**⚠️ Инвалидность:** Да")
        if person['relatives']:
            lines.append("")
            lines.append("**👨‍👩‍👧‍👦 Родственные связи:**")
            for relative in person['relatives']:
                relation = relative['relation']
                name = relative.get('name', '')
                birth_date = relative.get('birth_date', '')
                if birth_date:
                    lines.append(f"   • **{relation}:** {name} ({birth_date})")
                else:
                    lines.append(f"   • **{relation}:** {name}")
        if person['other']:
            for item in person['other']:
                lines.append(f"**ℹ️ {item}**")

        return '\n'.join(lines)