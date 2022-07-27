#import required libraries
from faulthandler import disable
from bs4 import BeautifulSoup as bs
from requests import get
from time import sleep
import json
import pandas as pd
from datetime import datetime
import ast
import logging
import pickle

logging.basicConfig(filename='logs.log', filemode='w', level=logging.INFO)

def get_html(url : str) -> bytes:
    """
    Get HTML from website
    :param url: URL of website we want HTML from
    :return: HTML content
    """
    response = get(url)
    html = response.content
    logging.info("Got html")
    return html


def make_soup(html : bytes) -> bs:
    """
    Make BeautifulSoup object from HTML for easier parsing
    :param html: HTML we want to parse
    """
    soup = bs(html, "lxml")
    logging.info("made soup")
    return soup


def get_all_car_brands(soup : bs) -> list:
    """
    Get all car brands from www.latribuneauto.com/
    :param bs: BeautifulSoup we want to find car brands from
    :return: list of car brands with spaces replaced with "-"
    """
    all_options = soup.find_all("option")
    all_options = all_options[1:-1]

    cars = []
    for option in all_options:
        cars.append(option.text.replace(" ", "-"))

    logging.info("Got car brands")

    return cars


def get_all_car_ids(soup : bs) -> list:
    """
    :param soup: BeautifulSoup object of the website
    :return: Return a list with all car ids in the same order as the list for all car brands
    """
    all_options = soup.find_all("option")
    all_options = all_options[1:-1]
    ids = []
    for option in all_options:
        ids.append(option["value"])
    logging.info("Got car ids")
    return ids

def get_all_car_models(new_or_old : str, car_brands : list, car_ids : list) -> dict:
    """
    Create a dict linking car brands to car models
    :param new_or_old: <new> or <old> depending on which we want to search for (new cars or used cars)
    :param car_brands: list of car brands (make sure that the list contains the old cars if new_or_old is old and vice versa)
    :param car_ids: list of car brand ids (make sure that the list contains the old car ids if new_or_old is old and vice versa)
    :return: dictionary of lists which links car brands to car models
    """
    all_models = {}
    for car_brand in car_brands:
        if new_or_old == "new":
            html = get_html("https://www.latribuneauto.com/prix/voitures-neuves?search[brand]=" + str(car_ids[car_brands.index(car_brand)]))
        elif new_or_old == "old":
            html = get_html("https://www.latribuneauto.com/cote-occasions/?search[brand]=" + str(car_ids[car_brands.index(car_brand)]))
        soup = make_soup(html)
        models_html = soup.find_all(name = "select", id = "search_model")[0]
        models = []
        for model in models_html.find_all("option"):

            #String sanitisation as spaces and + do not play well with links
            model = model.text.replace(" ", "-")
            if model[-1] == "+":
                model = model.replace("+", "")
            else:
                model = model.replace("+", "-")
            model = model.replace("'", "-")


            models.append(model)
        all_models[car_brand] = models
        print("Got models for " + car_brand)
    
    if new_or_old == "new":
        save_dict(all_models, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\car_models.json")
    elif new_or_old == "old":
        save_dict(all_models, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\car_models_old.json")
    
    logging.info("Got car models")

    return all_models


def get_all_car_submodels_info(car_models : dict) -> dict:
    """
    Records car submodel name, price and CO2 emission
    :param car_models: dictionary of lists which links car brands to car models
    :return: dictionary which links car model to submodel info
    """
    brand_and_model_to_submodel = {}
    for brand in car_models:
        for model in car_models[brand]:
            html = get_html(f"https://www.latribuneauto.com/caracteristiques-voitures-neuves/{brand}/modele/{model}")
            soup = make_soup(html)
            submodels_html = soup.find_all("tbody")
            if len(submodels_html) == 1:
                submodels_html = submodels_html[0]
                brand_and_model_to_submodel[(brand, model)] = list(submodels_html.stripped_strings)
            elif len(submodels_html) > 1:
                submodels_html = submodels_html[1]
                brand_and_model_to_submodel[(brand, model)] = list(submodels_html.stripped_strings)
            else:
                brand_and_model_to_submodel[(brand, model)] = []

            logging.info("Done with " + brand + ": " + model)

        
       
    save_dict_as_str(brand_and_model_to_submodel, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\submodels_info.txt")
    return brand_and_model_to_submodel

def get_old_car_submodels_dates(car_models : dict) -> dict:
    """
    Get list of valid dates for old car models. This range is current_year - 3 to current_year
    :param car_models: dictionary of lists which links car brands to car models
    :return: dictionary which links car brand and model to a list of valid dates
    """
    
    year = datetime.today().year 
    min_year = year - 3
    model_to_dates = {}
    for brand in car_models:
        for model in car_models[brand]:


            html = get_html(f"https://www.latribuneauto.com/cote-occasions/{brand}/modele/{model}")
            soup = make_soup(html)

            years_html = soup.find_all(name = "div", id = "years-module")[0]
            all_years = list(years_html.stripped_strings)[1:]
            valid_years_in_html = []
            for i in all_years:
                if year >= int(i) >= min_year:
                    valid_years_in_html.append(int(i))

            model_to_dates[(brand, model)] = valid_years_in_html

        
            
    save_dict_as_str(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\model_to_dates_new.txt.py")
    return model_to_dates
            
def get_all_old_car_submodels_info(brand_and_model_to_dates : dict) -> dict:
    """
    Get information about old car submodels
    :param brand_and_model_to_dates: dictionary which links car brand and model to a list of valid dates
    :return: dictionary which links car brand, model and date to submodel information
    """
    brand_and_model_and_year_to_submodels = {}

    for brand, model in brand_and_model_to_dates:
        for year in brand_and_model_to_dates[(brand, model)]:
            html = get_html(f"https://www.latribuneauto.com/caracteristiques-voitures-occasions/{brand}/modele/{model}/{year}")
            soup = make_soup(html)
            submodels_html = soup.find_all("tbody")
            if len(submodels_html) == 1:
                submodels_html = submodels_html[0]
                brand_and_model_and_year_to_submodels[(brand, model, year)] = list(submodels_html.stripped_strings)
            elif len(submodels_html) > 1:
                submodels_html = submodels_html[1]
                brand_and_model_and_year_to_submodels[(brand, model, year)] = list(submodels_html.stripped_strings)
            else:
                brand_and_model_and_year_to_submodels[(brand, model, year)] = []

    save_dict_as_str(brand_and_model_and_year_to_submodels, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\old_submodels_info.txt")
    return brand_and_model_and_year_to_submodels




def clean_submodels_info(submodels_info : dict) -> dict:
    """
    Clean dictionary generated by get_all_car_submodels_info() so that we can turn it into a pandas dataframe
    :param submodels_info: dictionary returned by get_all_car_submodels_info
    :return: dictionary containing info about car submodels
    """
    brand_and_model_and_submodel_to_info = {}
    for brand, model in submodels_info: 
        all_submodels = submodels_info[(brand, model)]
        container = []
        specific_submodel = []
        for datapoint in all_submodels:
            if datapoint != "2":
                specific_submodel.append(datapoint)
            if datapoint == "2":
                container.append(specific_submodel)
                specific_submodel = []
                
        duplicate_key_counter = 0
        for submodel_info in container:
            key = (brand, model, submodel_info[0])
            if key in brand_and_model_and_submodel_to_info:
                key = (brand, model, submodel_info[0] + "(" + str(duplicate_key_counter) + ")")
                duplicate_key_counter += 1
            
            if len(submodel_info[1:]) == 1:
                if "€" in submodel_info:
                    brand_and_model_and_submodel_to_info[key] = {"price" : submodel_info[1], "CO2_emissions" : None, "url" : f"https://www.latribuneauto.com/caracteristiques-voitures-neuves/{brand}/modele/{model}"}
                else:
                    brand_and_model_and_submodel_to_info[key] = {"price" : None, "CO2_emissions" : submodel_info[1], "url" : f"https://www.latribuneauto.com/caracteristiques-voitures-neuves/{brand}/modele/{model}"}
            else:
                brand_and_model_and_submodel_to_info[key] = {"price" : submodel_info[1], "CO2_emissions" : submodel_info[2], "url" : f"https://www.latribuneauto.com/caracteristiques-voitures-neuves/{brand}/modele/{model}"}

    save_dict_as_str(brand_and_model_and_submodel_to_info, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\submodels_info_clean.txt")
    return brand_and_model_and_submodel_to_info 



def clean_submodels_info_old(submodels_info : dict) -> dict:
    """
    Clean dictionary generated by get_all_old_car_submodels_info() so that we can turn it into a pandas dataframe
    :param submodels_info: dictionary which links car brand, model and date to submodel information
    :return: dictionary which links car band, model, date and submodel to information
    """
    brand_and_model_and_year_and_submodel_to_info = {}
    for brand, model, year in submodels_info:
        all_submodels = submodels_info[(brand, model, year)]
        container = []
        specific_submodel = []
        for datapoint in all_submodels:
            if datapoint != "2":
                specific_submodel.append(datapoint)
            if datapoint == "2":
                container.append(specific_submodel)
                specific_submodel = []
                
        duplicate_key_counter = 0
        for submodel_info in container:
            key = (brand, model, year, submodel_info[0])
            if key in brand_and_model_and_year_and_submodel_to_info:
                key = (brand, model, year, submodel_info[0] + "(" + str(duplicate_key_counter) + ")")
                duplicate_key_counter += 1
            
            if len(submodel_info[1:]) == 1:
                if "€" in submodel_info:
                    brand_and_model_and_year_and_submodel_to_info[(brand, model, year, submodel_info[0])] = {"price" : submodel_info[1], "CO2_emissions" : None, "url" : f"https://www.latribuneauto.com/caracteristiques-voitures-occasions/{brand}/modele/{model}/{year}"}
                else:
                    brand_and_model_and_year_and_submodel_to_info[(brand, model, year, submodel_info[0])] = {"price" : None, "CO2_emissions" : submodel_info[1], "url" : f"https://www.latribuneauto.com/caracteristiques-voitures-occasions/{brand}/modele/{model}/{year}"}

            else:
                brand_and_model_and_year_and_submodel_to_info[(brand, model, year, submodel_info[0])] = {"price" : submodel_info[1], "CO2_emissions" : submodel_info[2], "url" : f"https://www.latribuneauto.com/caracteristiques-voitures-occasions/{brand}/modele/{model}/{year}"}

    save_dict_as_str(brand_and_model_and_year_and_submodel_to_info, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\old_submodels_info_clean.txt")
    return brand_and_model_and_year_and_submodel_to_info

def turn_dict_to_df_and_edit(dictionary : dict) -> pd.DataFrame:
    """
    Turn dict into a dataframe and keep only numbers in the price and CO2_emissions columns. Also add is_electric column which shows true if CO2_emissions is 0
    :param dictionary: dict to transform
    :return: clean df
    """
    df = pd.DataFrame(dictionary).transpose()
    
    df["price"].replace("[^0-9]", "", inplace = True, regex = True)

    df["CO2_emissions"].replace("[^0-9]", "", inplace = True, regex = True)
    
    df["CO2_emissions"] = df["CO2_emissions"].astype(int)

    df["is_electric"] = False

    df.loc[df["CO2_emissions"] == 0, "is_electric"] = True
    
    return df

def get_hrefs_for_electric_submodels(df : pd.DataFrame) -> tuple:
    
    indices = df[df["is_electric"]].index.tolist()

    hrefs = []
    
    for index in indices:
        url = df.iloc[index, 5]

        submodel = df.iloc[index, 2]

        html = get_html(url)

        soup = make_soup(html)

        href = soup.find("strong", text = submodel).parent.get("href")

        print(href)

        hrefs.append(href)
    
    save_list(hrefs, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\hrefs.P")

    return (indices, hrefs)


def get_autonomous_range(href : str) -> str:
    url = "https://www.latribuneauto.com" + href[:-10] + "caracteristiques"

    html = get_html(url)

    soup = make_soup(html)

    child_soup = soup.find("td", text = "Autonomie mode électrique (km)")
    
    try:
        string_content = list(child_soup.parent.stripped_strings)
    
    #if there is no field for Autonomie mode électrique (km)
    except Exception as ex:
        string_content = []

    #if either Autonomie mode électrique (km) or the value is missing
    if len(string_content) < 2:
        autonomous_distance = None
    else:
        autonomous_distance = string_content[1]

    print(url)
    print(autonomous_distance)
    print("-" * 50)

    return autonomous_distance


def get_all_autonomous_range(hrefs : list) -> list:
    autonomous_ranges = []
    for href in hrefs:
        distance = get_autonomous_range(href)
        if distance is not None:

            distance = int(distance)

            if distance > 1000:
                distance = round(distance / 1000)
        
        autonomous_ranges.append(distance)

    save_list(autonomous_ranges, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\autonomous_ranges.P")
    return autonomous_ranges

    

        



        

    



def save_dict(var, path_to_file):
    with open(path_to_file, "w") as tf:
        json.dump(var, tf)
        tf.close()
    
def read_dict(path : str):
    with open(path) as f:
        data = f.read()
        dict = json.loads(data)
    return dict

def save_dict_as_str(var : dict, path : str):
    save_str = str(var)
    text_file = open(path, 'w')
    text_file.write(save_str)
    text_file.close()

def read_dict_as_str(path : str) -> dict:
    text_file = open(path, 'r')
    dictionary = ast.literal_eval(text_file.read())
    text_file.close()
    return dictionary

def save_list(lst : list, path : str):
    with open(path, "wb") as output:
        pickle.dump(lst, output)

def read_list(path : str) -> list:
    with open(path, "rb") as input:
        lst = pickle.load(input)
    return lst



def main(): 

    r"""html = get_html("https://www.latribuneauto.com/prix/voitures-neuves")
    print("Got html")

    soup = make_soup(html)
    print("Made soup")

    car_brands = get_all_car_brands(soup)
    print("Got car brands")

    car_ids = get_all_car_ids(soup)
    print("Got car ids")

    car_models = get_all_car_models("new", car_brands, car_ids)
    print("Got car models")

    submodels_info = get_all_car_submodels_info(car_models)
    print("Got car submodels")

    final = clean_submodels_info(submodels_info)
    print("Cleaned dict")

    df = turn_dict_to_df_and_edit(final)
    print("Turned into df")
    
    indices, hrefs = get_hrefs_for_electric_submodels(df)
    """

    df = pd.read_csv(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\final.csv")

    indices = df[df["is_electric"]].index.tolist()

    hrefs = read_list(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\hrefs.P")

    autonomous_ranges = read_list(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\autonomous_ranges.P")

    df["autonomous_range"] = None

    for i in range(len(indices)):
        df.iloc[indices[i], 7] = autonomous_ranges[i]


    df.to_csv(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\df_with_range.csv")

    

    
    


    
    



def main_old():

    html = get_html("https://www.latribuneauto.com/cote-occasions/")
    print("Got html")

    soup = make_soup(html)
    print("Made soup")

    car_brands = get_all_car_brands(soup)
    print("Got car brands")

    car_ids = get_all_car_ids(soup)
    print("Got car ids")

    car_models = get_all_car_models("old", car_brands, car_ids)
    print("Got car models")

    models_dates = get_old_car_submodels_dates(car_models)
    print("Got car dates")
    
    submodels_info = get_all_old_car_submodels_info(models_dates)
    print("Got car submodels")

    final = clean_submodels_info_old(submodels_info)
    print("Cleaned dict")

    df = turn_dict_to_df_and_edit(final)
    print("Turned into df")
    
    


    df.to_csv(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\final_old.csv")



    r"""car_models = read_dict(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\car_models_old.json")

    brand_and_model_to_dates = read_dict_as_str(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\model_to_dates_new.json")

    submodels_info = read_dict_as_str(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\old_submodels_info.txt")"""

main()
