from urllib.request import urlopen
from urllib.request import HTTPError
from urllib.request import URLError
from bs4 import BeautifulSoup
import ssl
import re
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DATA_FILE='/persistent/products.json'

def load_previous_data():
    """Загружаем сохраненные данные"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}

def save_current_data(data):
    """Сохраняем текущие данные"""
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def get_current_products():
    """ Получаем новый список наличия у поставщика """
    ssl._create_default_https_context = ssl._create_unverified_context
    try:
        html = urlopen('https://yushkoff.com/cassowary-australia.html')
    except HTTPError as e:
        print(e)
    except URLError as e:
        print('The server could not be found!')
        
    bs = BeautifulSoup(html, 'html.parser')
    tshirts = bs.find_all('div',{'class': 'ty-grid-list__item ty-quick-view-button__wrapper'})
    products = {}
    for tshirt in tshirts:
        name = tshirt.find('a',{'class': 'product-title'})
        article = tshirt.find('div',{'art'})
        selection = tshirt.find('select', {'name':re.compile('sizeselect.*')})
        sizes = [size.text for size in selection.find_all('option')]
        products[name.attrs['title'] + ' ' + article.text] = sizes
        # print(name.attrs['title'] + ' ' + article.text)
        # print(sizes)
    return products

def compare_products(old_data, new_data):
    """ Сравниваем старые и новые данные """
    old_keys = set(old_data.keys())
    new_keys = set(new_data.keys())

    appeared_products = new_keys - old_keys # новые товары
    disappeared_products = old_keys - new_keys # удаленные товары

    changed_products = {} # товары, у которых изменились артикулы

    for key in old_keys & new_keys: # проверяем только те товары, которые остались
        old_articles = set(old_data[key])
        new_articles = set(new_data[key])

        added_articles = new_articles - old_articles
        removed_articles = old_articles - new_articles

        if added_articles or removed_articles:
            changed_products[key] = {
                "added": list(added_articles),
                "removed": list(removed_articles)
            }
    return (
            {key: new_data[key] for key in appeared_products},
            {key: old_data[key] for key in disappeared_products},
            changed_products
    )

def send_mail(text):
    """
    Отправляем по почте изменения наличия
    """
    # Настройки почтового сервера
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_SENDER = "alek200673@gmail.com"
    EMAIL_PASSWORD = "bzii jctf rrxb rbwx"
    EMAIL_RECEIVER = "mountainshirt@gmail.com"
    
    # Создание email
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = "Cassowary stock has changed"
    msg.attach(MIMEText(text, "plain"))
    
    # Отправка email
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Защищенное соединение
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        return("✅ Письмо успешно отправлено!")
    except Exception as e:
        return(f"❌ Ошибка при отправке письма: {e}")
    
    

def main():
    old_data = load_previous_data()
    new_data = get_current_products()

    appeared, disappeared, changed = compare_products(old_data, new_data)

    text_to_send = ''

    print("Появились новые товары:")
    for key, articles in appeared.items():
        print(f" - Артикул: {key}, Размеры: {', '.join(articles)}")
        text_to_send += 'New t-shirts: '+ key +', '.join(articles)+'\n'
    print("Исчезли товары")
    for key, articles in disappeared.items():
        print(f" - Артикул: {key}, Размеры: {', '.join(articles)}")
        text_to_send += 'T-shorts is over: '+ key +', '.join(articles)+'\n'
    print("\n Изменения в артикулах товаров:")
    for key, changes in changed.items():
        print(f" - Артикул: {key}")
        if changes["added"]:
            print(f" Добавлены размеры: {', '.join(changes['added'])}")
            text_to_send += 'New sizes of t-shirts: '+ key +', '.join(changes['added'])+'\n'
        if changes["removed"]:
            print(f" Удалены размеры: {', '.join(changes['removed'])}")
            text_to_send += 'Sizes of t-shirts has gone: '+ key +', '.join(changes['removed'])+'\n'
    save_current_data(new_data)

    if len(text_to_send):
        print(send_mail(text_to_send))

    
if __name__ == "__main__":
    main()
