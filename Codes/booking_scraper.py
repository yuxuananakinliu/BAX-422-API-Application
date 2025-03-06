from urllib.parse import urlencode
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.common import NoSuchElementException
import csv



# Exception function
def handle_no_such_element_exception(data_extraction_task):
    try:
        return data_extraction_task()
    except NoSuchElementException as e:
        return None
    


def get_hotel_detail(
        city:str, 
        checkin:str, 
        checkout:str,
        adult_count:int,
        child_count:int,
        room_count:int, 
        stars:list[int], 
        currency:str='USD', 
        language:str='en-us',
        output_csv:bool=False
    )->list[dict[str, any]]:
    # create a Chrome web driver instance
    driver = webdriver.Chrome(service=Service())

    # connect to the target page
    url = "https://www.booking.com/searchresults.html?"

    star_class = ''
    for s in stars:
        star_class += f'class%3D{s}%3B'
    star_class = star_class[:-3]

    params = {
        'ss':city.replace(" ", "+"),
        'lang':language,
        'checkin':checkin,
        'checkout':checkout,
        'group_adults':str(adult_count),
        'no_rooms':str(room_count),
        'group_children':str(child_count),
        'selected_currency':currency,
        'nflt':star_class
    }

    url = url + urlencode(params, doseq=True) + f'&nflt={star_class}'
    driver.get(url)

    # Handle sign-in alert
    try:
        close_button = WebDriverWait(driver, 7).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[role=\"dialog\"] button[aria-label=\"Dismiss sign-in info.\"]")
            )
        )
        close_button.click()
    except TimeoutException:
        print("Sign-in modal did not appear, continuing...")

    # Store items scraped
    items = []

    # select all property items on the page
    property_items = driver.find_elements(By.CSS_SELECTOR, "[data-testid=\"property-card\"]")

    # Scrape looping
    for property_item in property_items:
        # Scrape Hotel name
        title = handle_no_such_element_exception(lambda: property_item.find_element(
            By.CSS_SELECTOR, "[data-testid=\"title\"]"
        ).text)

        # Scrape reviews
        review_score = None
        review_count = None
        review_text = handle_no_such_element_exception(lambda: property_item.find_element(
            By.CSS_SELECTOR, "[data-testid=\"review-score\"]"
        ).text)
        if review_text is not None:
            parts = review_text.split("\n")
            for part in parts:
                part = part.strip()
                # check potential review score
                if part.replace(".", "", 1).isdigit():
                    review_score = float(part)
                # check if it contains the "reviews"
                elif "reviews" in part:
                    review_count = int(part.split(" ")[0].replace(",", ""))

        # Scrape pricing information
        price_element = handle_no_such_element_exception(lambda: (
            property_item.find_element(By.CSS_SELECTOR, "[data-testid=\"availability-rate-information\"]")
        ))
        if price_element is not None:
            original_price = handle_no_such_element_exception(lambda: (
                price_element.find_element(By.CSS_SELECTOR, "[aria-hidden=\"true\"]:not([data-testid])").text.replace(",", "")
            ))
            price = handle_no_such_element_exception(lambda: (
                price_element.find_element(By.CSS_SELECTOR, "[data-testid=\"price-and-discounted-price\"]").text.replace(",", "")
            ))

        # populate a new item with the scraped data
        item = {
            "hotel_name": title,
            "review_score": review_score,
            "review_count": review_count,
            "price": price
        }
        # add the new item to the list of scraped items
        items.append(item)

    if output_csv:
        output_file = "properties.csv"

        # export the items list to a CSV file
        with open(output_file, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file, 
                fieldnames=["hotel_name", "review_score", "review_count", "price"]
            )
            writer.writeheader()
            writer.writerows(items)

    # Close the web driver
    driver.quit()

    return items