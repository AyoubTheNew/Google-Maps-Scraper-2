from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from parsel import Selector
import time
import sys
from PlacesVisualiser import *
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin

googleAcceptButtonClicked = False

# setUpWebDriver
options = webdriver.ChromeOptions()
options.add_argument('headless')  # Make browser open in background
# driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
driver = webdriver.Chrome(ChromeDriverManager().install())
driver.maximize_window()

def check_exists_by_xpath(xpath):
    """
    This function checks if the element specified by the xpath is present at the website.
    It is used to check if any places are available in the Google Maps searching results' menu.

    :param xpath: the xpath of searched element
    :return: boolean value corresponding to the existence of the searched element
    """
    try:
        driver.find_element(By.XPATH, xpath)
    except NoSuchElementException:
        return False
    return True


def scrollDownLeftMenuOnGoogleMaps(counter, waitingTime):
    """
    This function is responsible for scrolling down the menu visible at the left.
    It is used while searching for places at Google Maps. It allows seeing more places relevant for the search value.

    :param counter: number of scrolls down
    :param waitingTime: waiting time until next scroll (new results are loaded)
    """
    menu_xpath = 'id("QA0Szd")/DIV[1]/DIV[1]/DIV[1]/DIV[2]/DIV[1]/DIV[1]/DIV[1]/DIV[1]/DIV[1]/DIV[1]'
    if check_exists_by_xpath(menu_xpath):
        total_length = 0
        for i in range(counter):
            # wait until element is located
            wait = WebDriverWait(driver, waitingTime)
            menu_left = wait.until(EC.visibility_of_element_located((By.XPATH, menu_xpath)))

            # get the initial length of the menu
            initial_length = len(menu_left.text)

            # perform scrolling down
            scroll_origin = ScrollOrigin.from_element(menu_left)
            ActionChains(driver).scroll_from_origin(scroll_origin, 0, 150).perform()

            # wait for the menu to load new results
            time.sleep(waitingTime)

            # get the new length of the menu
            new_length = len(menu_left.text)

            # calculate the length difference
            length_difference = new_length - initial_length
            total_length += length_difference
            print(f"Length difference after scroll {i+1}: {total_length}")
            
def searchForPlace(url, typeOfPlace):
    """
    This function is responsible for searching a place of specific type at specific location with set zoom.
    All information about searching are contained in the URL.

    :param url: path which is inserted into browser
    :param typeOfPlace: type of place searched in Google Maps
    :return: dictionary containing places found using this URL
    """
    global googleAcceptButtonClicked
    driver.get(url)
    
    # only at the first page click the "accept all" ("zaakceptuj wszystko") button
    if not googleAcceptButtonClicked:
        clickAcceptAllButton()
    # get the source code of the page
    page_content = driver.page_source
    response = Selector(page_content)
    # scroll down left menu
    placesResults = []
    titles = set()  # Create a set to store unique titles
    while True:
        page_content = driver.page_source
        response = Selector(page_content)
        # save the search results into a dictionary
        for idx, el in enumerate(response.xpath('//div[contains(@aria-label, "Résultats")]/div/div[./a]')):
            link = el.xpath('./a/@href').extract_first('')
            title = el.xpath('./a/@aria-label').extract_first('')
            if title in titles:
                continue
            titles.add(title)
            # Find the elements right before you interact with them
            elements = driver.find_elements(By.XPATH,'//div[contains(@aria-label, "Résultats")]/div/div[./a]')
            wait = WebDriverWait(driver, 10) 
            if idx == 0:
                elements[idx].click()
                time.sleep(5)  # Wait for 5 seconds if it's the first element
            else:
                elements[idx].click()
                time.sleep(1) 
            # Get the phone number
            try:
                phone_div = driver.find_element(By.XPATH, 'id("QA0Szd")//div/BUTTON[contains(@aria-label, "Numéro de téléphone:")]')
                phone_number = phone_div.get_attribute('aria-label')
                phone_number = ''.join(filter(str.isdigit, phone_number))  # Extract only digits from phone_number
                print(f'{title}: {phone_number}')
            except NoSuchElementException:
                continue
            # add all information about the place to the dictionary
            placesResults.append({
                'link': link,
                'title': title,
                'type': typeOfPlace,
                'phone_number': phone_number})
            # Check if there is a next element
            if idx < len(elements) - 1:  
                driver.execute_script("arguments[0].scrollIntoView();", elements[idx+1])
            close_button = driver.find_element(By.CSS_SELECTOR, 'button.VfPpkd-icon-LgbsSe')
            close_button.click()
            WebDriverWait(driver, 10).until(EC.staleness_of(close_button))
            
        scrollDownLeftMenuOnGoogleMaps(counter=1, waitingTime=0)
        if check_exists_by_xpath('//span[contains(text(), "Vous êtes arrivé à la fin de la liste.")][last()]'):
            if check_exists_by_xpath('//span[contains(text(), "Vous êtes arrivé à la fin de la liste.")][last()]'):
                scrollDownLeftMenuOnGoogleMaps(counter=1, waitingTime=15)
                WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.XPATH, '//span[contains(text(), "Vous êtes arrivé à la fin de la liste.")][last()]')))
                break
    return placesResults



def clickAcceptAllButton():
    """
    This function is responsible for clicking "accept all" button at the first page opened after initialization of
    the webdriver.
    """
    global googleAcceptButtonClicked
    #button_path = '//*[@id="yDmH0d"]/c-wiz/div/div/div/div[2]/div[1]/div[3]/div[1]/div[1]/form[2]/div/div/button'
    #wait = WebDriverWait(driver, 10)
    #button = wait.until(EC.visibility_of_element_located((By.XPATH, button_path)))
    #button.click()
    googleAcceptButtonClicked = True


def addLonLatToDataFrame(df):
    """
    This function adds columns "lat" (latitude) and "lon" (longitude) to dataframe containing list of found places.

    :param df: dataframe containing list of found places
    :return: dataframe containing list of found places and each place has assigned latitude and longitude
    """
    if 'link' in df.columns:
        df[['lat', 'lon']] = df['link'].str.extract(r'!3d(.*?)!16.*!4d(.*?)!', expand=True)
        df = df[['lat', 'lon', 'type', 'title','link']]  # set order of columns

    return df


def closeDriver():
    """
    This function quits the driver. Driver is created at the beginning of MainScrapper file.
    """
    driver.quit()


def generateUrls(typeOfPlace):
    """
    This function generated urls which are used during searching for places of specific type.

    :param typeOfPlace: type of place searched in Google Maps
    :return: list of generated URLs containing type of place, searched location, and zoom of searching
    """
    pointsDirectory = "generatedPoints/"
    points_df = pd.read_csv(pointsDirectory + "measure_points_3r_3c.csv", index_col=False)

    base = 'https://www.google.com/maps/search/'

    generated_urls = []

    for index, row in points_df.iterrows():
        point_lat = points_df.at[index, 'lat']
        point_lon = points_df.at[index, 'lon']
        zoom = 16
        url = base
        url += str(typeOfPlace) + '/@'
        url += str(point_lat) + ',' + str(point_lon) + ',' + str(zoom) + 'z'
        generated_urls.append(url)
    return generated_urls


if __name__ == "__main__":

    start = time.time()

    # check if any types are specified in the arguments
    types_of_places = sys.argv[1:]

    if len(types_of_places) == 0:
        types_of_places = ['cenima']  # set the types of searched places

    print(types_of_places)
    for typeOfPlace in types_of_places:

        urls = generateUrls(typeOfPlace)

        print("total number of points to check:" + str(len(urls)))

        list_of_places = []
        progressCounter = 0
        for url in urls:
            new_places = searchForPlace(url, typeOfPlace)
            if not new_places:
                print(f"No places returned from searchForPlace for url: {url}")
            list_of_places += new_places  # concat two lists
            progressCounter += 1
            print("progress: " + str(round(100 * progressCounter / len(urls), 2)) + "%")

        if not list_of_places:
            print("No places found for typeOfPlace: " + typeOfPlace)
        else:
            df = pd.DataFrame(list_of_places)

            df_before_drop = df.copy()
            df = df.drop_duplicates()
            if df_before_drop.shape[0] > df.shape[0]:
                print("Duplicates were dropped from the DataFrame")

            df_before_lonlat = df.copy()
            df = addLonLatToDataFrame(df)
            if df_before_lonlat.shape[0] > df.shape[0]:
                print("Rows were removed in addLonLatToDataFrame")

            print("number of places:" + str(df.shape[0]))

            df.to_csv('database/' + typeOfPlace + '_v1.csv', index=False)

    closeDriver()

    end = time.time()
    print("total time:" + str(end - start) + " seconds --> " + str((end - start) / 60) + " minutes")
