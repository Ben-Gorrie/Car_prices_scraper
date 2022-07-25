#import required libraries
from bs4 import BeautifulSoup as bs
from requests import get
from time import sleep
import json
import pandas as pd
from datetime import datetime
import ast
import logging

logging.basicConfig(filename='logs.log', filemode='w', level=logging.INFO)

def get_html(url : str) -> bytes:
    response = get(url)
    html = response.content
    return html



def make_soup(html : bytes) -> bs:
    soup = bs(html, "lxml")
    return soup


def get_all_car_brands(soup : bs) -> list:
    all_options = soup.find_all("option")
    all_options = all_options[1:-1]

    cars = []
    for option in all_options:
        cars.append(option.text.replace(" ", "-"))

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
    :param new_or_old: <new> or <old> depending on which we want to search for (new or used)
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
            model = model.text.replace(" ", "-")
            if model[-1] == "+":
                model = model.replace("+", "")
            else:
                model = model.replace("+", "-")
            model = model.replace("'", "-")
            models.append(model)
        all_models[car_brand] = models
    
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
    model_to_submodel = {}
    for brand in car_models:
        for model in car_models[brand]:
            html = get_html(f"https://www.latribuneauto.com/caracteristiques-voitures-neuves/{brand}/modele/{model}")
            soup = make_soup(html)
            submodels_html = soup.find_all("tbody")
            if len(submodels_html) == 1:
                submodels_html = submodels_html[0]
                model_to_submodel[model] = list(submodels_html.stripped_strings)
            elif len(submodels_html) > 1:
                submodels_html = submodels_html[1]
                model_to_submodel[model] = list(submodels_html.stripped_strings)
            else:
                model_to_submodel[model] = []
       
    save_dict(model_to_submodel, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\submodels_info.json")
    return model_to_submodel

def get_old_car_submodels_dates(car_models : dict) -> dict:
    model_to_dates = {}
    for brand in car_models:
        for model in car_models[brand]:


            html = get_html(f"https://www.latribuneauto.com/cote-occasions/{brand}/modele/{model}")
            soup = make_soup(html)

            years_html = soup.find_all(name = "div", id = "years-module")[0]
            all_years = list(years_html.stripped_strings)[1:]
            valid_years_in_html = []
            for i in all_years:
                if int(i) >= datetime.today().year - 3:
                    valid_years_in_html.append(int(i))

            model_to_dates[(brand, model)] = valid_years_in_html

            logging.info(model)
            logging.info(model_to_dates[(brand, model)])
    
    #save_dict(model_to_dates, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices\model_to_dates.json")
    save_dict_as_str(model_to_dates, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\model_to_dates_new.txt")
    logging.info("Got model dates")
    return model_to_dates
            
def get_all_old_car_submodels_info(brand_and_model_to_dates : dict) -> dict:

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
        logging.info("Done with " + brand + ": " + model)


    #save_dict_as_str(brand_and_model_and_year_to_submodels, "/home/bengorrie/Car_prices_scraper/old_submodels_info.txt")

    save_dict_as_str(brand_and_model_and_year_to_submodels, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\old_submodels_info.txt")
    return brand_and_model_and_year_to_submodels

   


def clean_submodels_info(submodels_info : dict) -> dict:
    """
    Changes the structure of the submodels_info dictionary from dict of lists (e.g. {model : [submodel info]} ) to dict of dict of dict (e.g {model : {submodel_name : {price : xx, CO2 : xx}}} )
    :param submodels_info: dictionary returned by get_all_car_submodels_info
    :return: structured nested dictionary containing info about car submodels
    """
    for model in submodels_info.keys():
        res = {}
        del submodels_info[model][3::4]
        submodels = submodels_info[model][::3]
        prices = submodels_info[model][1::3]
        CO2_emissions = submodels_info[model][2::3]
        
        for i in range(len(submodels) - 1):
            res[submodels[i]] = {"price" : prices[i], "CO2_emissions": CO2_emissions[i]}
        submodels_info[model] = res
    save_dict(submodels_info, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices\submodels_info_clean.json")
    return submodels_info

def clean_submodels_info_old(submodels_info : dict) -> dict:

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
        for submodel_info in container:
            if len(submodel_info[1:]) == 1:
                brand_and_model_and_year_and_submodel_to_info[(brand, model, year, submodel_info[0])] = {"price" : None, "CO2_emissions" : submodel_info[1]}

            else:
                brand_and_model_and_year_and_submodel_to_info[(brand, model, year, submodel_info[0])] = {"price" : submodel_info[1], "CO2_emissions" : submodel_info[2]}

            logging.info(f"{brand} : {model} : {year} : {submodel_info[0]}")
            logging.info(brand_and_model_and_year_and_submodel_to_info[(brand, model, year, submodel_info[0])])
    






    #save_dict_as_str(brand_and_model_and_year_and_submodel_to_info, "/home/bengorrie/Car_prices_scraper/old_submodels_info_clean.txt")
    save_dict_as_str(brand_and_model_and_year_and_submodel_to_info, r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\old_submodels_info_clean.txt")

    return brand_and_model_and_year_and_submodel_to_info



def create_final_dict(car_models : dict, submodels_info : dict) -> dict:
    """
    Link all previous dictionaries together to get a dictionary of the form {brand : {model : {submodel : {submodel info}}}}
    :param car_models: dictionary of lists which links car brands to car models
    :param submodels_info: structured nested dictionary containing info about car submodels
    :return: dictionary as described above
    """
    final = {}
    for brand, models in car_models.items():
        for model in models:
            for submodel, info in submodels_info[model].items():
                final[(brand, model, submodel)] = info
    return final
            

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


def main(): 

    html = get_html("https://www.latribuneauto.com/prix/voitures-neuves")

    soup = make_soup(html)

    car_brands = get_all_car_brands(soup)

    car_ids = get_all_car_ids(soup)

    car_models = get_all_car_models("new", car_brands, car_ids)

    submodels_info = get_all_car_submodels_info("new", car_models)

    submodels_info = clean_submodels_info(submodels_info)

    final = create_final_dict(car_models, submodels_info)


    df = pd.DataFrame(final).transpose()

    df["price"].replace("[^0-9]", "", inplace = True, regex = True)

    df["CO2_emissions"].replace("[^0-9]", "", inplace = True, regex = True)
    
    df["CO2_emissions"] = df["CO2_emissions"].astype(int)

    df["is_electric"] = False

    df.loc[df["CO2_emissions"] == 0, "is_electric"] = True


    df.to_csv(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices\final.csv")

def main_old():

    html = get_html("https://www.latribuneauto.com/cote-occasions/")

    soup = make_soup(html)

    car_brands = get_all_car_brands(soup)

    car_ids = get_all_car_ids(soup)

    car_models = get_all_car_models("old", car_brands, car_ids)

    models_dates = get_old_car_submodels_dates(car_models)
    
    submodels_info = get_all_old_car_submodels_info(models_dates)

    final = clean_submodels_info_old(submodels_info)


    df = pd.DataFrame(final).transpose()

    df["price"].replace("[^0-9]", "", inplace = True, regex = True)

    df["CO2_emissions"].replace("[^0-9]", "", inplace = True, regex = True)

    df["CO2_emissions"] = df["CO2_emissions"].astype(int)

    df["is_electric"] = False

    df.loc[df["CO2_emissions"] == 0, "is_electric"] = True


    df.to_csv(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\final_old.csv")









    r"""car_models = read_dict(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\car_models_old.json")

    brand_and_model_to_dates = read_dict_as_str(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\model_to_dates_new.json")

    submodels_info = read_dict_as_str(r"C:\Users\BenjaminGORRIE\OneDrive - Ekimetrics\Documents\Car_prices_scraper\old_submodels_info.txt")"""

    






    
main_old()
