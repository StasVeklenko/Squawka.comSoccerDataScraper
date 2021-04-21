from scrapy_splash import SplashRequest
from scrapy import Spider
from scrapy.projects.squawka.squawka.excel import spreadsheet
from bs4 import BeautifulSoup
from collections import OrderedDict
import codecs, win_unicode_console

#REPEAT THIS WHOLE SPIDER 10 TIMES PER PAGE (THERE ARE 10 PAGES IN TOTAL AND CAN'T CRAWL THEM CONCURRENTLY)
class MySpider(Spider):
    name = 'spain_all_pages'
    url = 'http://www.squawka.com/match-results'
    page = 10
    match_links = list()
    fields_row = 4 #row of columns (fields) of table
    first_fields_column = 1 #column of a first field of table
    fields_amount = 14 #number of columns (fields)
    last_fields_column = first_fields_column + fields_amount - 1
    input_row = 5
    
    #scheme: do a request to initial url -> execute Lua script 'select La Liga, 2016/17 from the dropdown menus; collect all the links to pages with actual match data (for all pages)' -> after collection, go to each (one by one) 
    #start_requests() sets up the spanish parameters, parser just goes to links
    def start_requests(self):
        def return_match_list_script(page_number):
            
            match_list_script = """
            function main(splash, args)
              splash.private_mode_enabled = False
              
              assert(splash:go(args.url))
              
              assert(splash:wait(5))
              
              splash:evaljs("document.querySelector('div#sq-pagination span.current').nextElementSibling.click()")

              assert(splash:wait(3))
              
              splash:evaljs("document.querySelector(\\"select[id='league-filter-list'] option[value='23']\\").selected = true")
              
              assert(splash:wait(2))
              
              splash:evaljs("document.querySelector(\\"select[id='league-filter-list']\\").onchange()")
              
              assert(splash:wait(2))
              
              splash:evaljs("document.querySelector(\\"select[id='league-season-list'] option[value='2016']\\").selected = true")
              
              assert(splash:wait(2))
              
              splash:evaljs("document.querySelector(\\"select[id='league-season-list']\\").onchange()")
              
              assert(splash:wait(2))
              
              assert(splash:go("http://www.squawka.com/match-results?pg="""+page_number+""""))
              
              assert(splash:wait(3))
              
              return splash:html()
            end
            """  
            
            return match_list_script
        
        match_list_scripts = []
        win_unicode_console.enable()
        for page_number in range(self.page):
            match_list_scripts.append(return_match_list_script(str(page_number+1)))
        
        #match_list_scripts.append(return_match_list_script(str(self.page)))
        
        for match_list_script in match_list_scripts:    
            yield SplashRequest(self.url, self.parse_match_list,
                args={
                    'lua_source': match_list_script
                    # optional; parameters passed to Splash HTTP API
                    #'wait': 2,
                    # 'url' is prefilled from request url
                    # 'http_method' is set to 'POST' for POST requests
                    # 'body' is set to request body for POST requests
                },
                endpoint = '/execute'
                #slot_policy=scrapy_splash.SlotPolicy.PER_DOMAIN,  # optional
            )            
        
    def parse_match_list(self, response):
        #this function gets all the match links from response and puts them into match_links; then yields separate requests for each 
        self.match_links += response.xpath("//table[@class='fixture-results-table']/tbody/tr[@class='match-today']/td[@class='match-centre']/a/@href").extract()
        
        match_script = """
        function main(splash, args)
          splash.private_mode_enabled = False
          
          assert(splash:go(args.url))
          
          assert(splash:wait(5))
          
          local roomID = splash:evaljs("chatClient.roomID")
          
          assert(splash:wait(2))
          
          assert(splash:go("http://s3-irl-laliga.squawka.com/dp/ingame/"..roomID))
          
          assert(splash:wait(4)) 
        
          return splash:html()
        end
        """           
        '''
        button_names = response.xpath("//a[@class='pageing_text_arrow']/text()").extract()
        start_excel_input = False
        for button_name in button_names:
            if 'Next' in button_name:
                start_excel_input = True
                break
        '''
        
        current_page_number = response.xpath("//div[@id='sq-pagination'][1]//span[contains(@class, 'current')]/text()").extract()[0]
        start_excel_input = False
        if int(current_page_number) == self.page:
            start_excel_input = True
        
        if start_excel_input:
            for match_link in self.match_links:
                #self.logger.info("The link is: %s", match_link)
                yield SplashRequest(match_link, self.parse_match,
                    args={
                        'lua_source': match_script
                        # optional; parameters passed to Splash HTTP API
                        # 'wait': 2,
                        # 'url' is prefilled from request url
                        # 'http_method' is set to 'POST' for POST requests
                        # 'body' is set to request body for POST requests
                    },
                    endpoint = '/execute'
                    #slot_policy=scrapy_splash.SlotPolicy.PER_DOMAIN,  # optional
                ) 
        #else:
        #    page = response.xpath("//div[@id='sq-pagination']")[0].xpath(".//span[contains(@class, 'current')]/following-sibling::a[@class='page-numbers'][1]/text()").extract()[0]
        #    js = """splash:evaljs("document.querySelector(\\"a[href='http://www.squawka.com/match-results?pg="""+page+"""']\\").click()")"""
        #    print("gonna call start_requests now")
        #    self.start_requests(js_code = js)
        
    def parse_match(self, response):
        '''openpyxl API:
        opening workbook: workbook = openpyxl.load_workbook(workbook, keep_vba = True/False)
        opening worksheet: worksheet = workbook.get_sheet_by_name(worksheet_name)
        getting data: worksheet.cell(row,column).value
        setting data: worksheet.cell(row,column).value = data
        
        spreadsheet API:
        __init__(workbook, worksheet, keep_vba=False)
        get_data(worksheet, row_start, column_start, incr_step, number_of_incrs, incr_along)
        set_data(data, worksheet, row_start, column_start, incr_step, incr_along, workbook = "", keep_vba=False) 
        save(workbook="", keep_vba=False)
        
        Useful links on Scrapy:
        https://stackoverflow.com/questions/35720323/scrapyjs-splash-click-controller-button
        https://stackoverflow.com/questions/35052999/using-scrapyjs-crawl-onclick-pages-by-splash
        https://github.com/scrapinghub/splash/issues/200
        https://github.com/scrapy-plugins/scrapy-splash/issues/27
        '''
        
        player_ids = {}
        team_ids = {}        
        
        processed_xml = BeautifulSoup(str(response.body)[2:-1], "xml")
        
        #player ids
        for each in processed_xml.select("players player"):
            player_ids[each.get("id")] = [codecs.escape_decode(each.find("name").get_text().encode("latin-1"))[0].decode("utf-8"), each.get("team_id")]         
            
        #team ids
        for each in processed_xml.select("data_panel game team"):
            if each.find("state").get_text() == "home":
                home_team = codecs.escape_decode(each.find("short_name").get_text().encode("latin-1"))[0].decode("utf-8")
            elif each.find("state").get_text() == "away": 
                away_team = codecs.escape_decode(each.find("short_name").get_text().encode("latin-1"))[0].decode("utf-8")
            team_ids[each.get("id")] = [codecs.escape_decode(each.find("short_name").get_text().encode("latin-1"))[0].decode("utf-8"), each.find("state").get_text()]
        
        #setting up the main data container
        data = {
            'date': processed_xml.find("squawka").get("date"), #match date
            'home': home_team, #home team name
            'away': away_team, #away team name             
            'goals': {}, #type, player, is_own, mins
            'shots': {}, #type, player, mins
            'shots_on_target': {}, #type, player, mins
            'headed_duals': {}, #player (player_id), otherplayer, success/fail/foul, mins
            'interceptions': {}, #player, mins
            'clearances': {},  #type, player, mins
            'tackles': {}, #player (tackler), opponent (tacklee), success/fail/foul, mins
            'takeons': {}, #player (takeon-ee), other_player (takeon-er), success/fail, mins
            'blocked_events': {}, #player, blocked shot/pass/cross, mins
            'fouls': {}, #player (fouler), opponent (foulee), mins
            'cards': {} #player, card yellow/red, mins
        }      
        
        for key in data.keys():
            if key not in ['date', 'home', 'away']:
                data[key]["home_short"] = 0
                data[key]["away_short"] = 0
                data[key]["home_detailed"] = [] #list of dictionaries, sorted by mins (ascending) (will be sorted naturally, since events will be added in an ascending way)
                data[key]["away_detailed"] = [] #list of dictionaries, sorted by mins (ascending) (will be sorted naturally, since events will be added in an ascending way)      
        
        for key in data.keys():       
            if key in ['goals', 'shots', 'shots_on_target']:
                param_name = 'goals_attempts'
            else:
                param_name = key  
                
            if key not in ['date', 'home', 'away']:
                for event in processed_xml.select(param_name+' event'):
                    try: #appending data from xml to data
                        if key == "shots":
                            data[key][team_ids[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1, 'player': player_ids[event.get('player_id')][0], 'type': event.get('type'), "is_own": event.has_attr("is_own") }) 
                            if not event.has_attr("is_own"):
                                data[key][team_ids[event.get("team_id")][1]+"_short"] += 1
                        if key == "shots_on_target" and event.get("type") in ["save", "wood_work", "goal"]:
                            data[key][team_ids[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1, 'player': player_ids[event.get('player_id')][0], 'type': event.get('type'), "is_own": event.has_attr("is_own") }) 
                            if not event.has_attr("is_own"):
                                data[key][team_ids[event.get("team_id")][1]+"_short"] += 1 
                        elif key == 'goals' and event.get("type") == "goal":
                            data[key][team_ids[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1, 'player': player_ids[event.get('player_id')][0], 'type': event.get('type'), "is_own": event.has_attr("is_own") })
                            data[key][team_ids[event.get("team_id")][1]+"_short"] += 1
                        elif key == "headed_duals":
                            data[key][team_ids[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1, 'player': player_ids[event.get('player_id')][0], 'opponent': player_ids[event.find("otherplayer").get_text()][0], 'type': event.get("action_type") })
                            data[key][team_ids[event.get("team_id")][1]+"_short"] += 1
                        elif key == "interceptions":
                            data[key][team_ids[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1, 'player': player_ids[event.get('player_id')][0], 'headed': bool(event.find("headed")) })
                            data[key][team_ids[event.get("team_id")][1]+"_short"] += 1
                        elif key == "clearances":
                            data[key][team_ids[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1, 'player': player_ids[event.get('player_id')][0], 'headed': bool(event.find("headed").get_text()) })
                            data[key][team_ids[event.get("team_id")][1]+"_short"] += 1 
                        elif key == "tackles":
                            data[key][team_ids[event.find("tackler_team").get_text()][1]+"_detailed"].append({'mins': int(event.get("mins"))+1, 'player': player_ids[event.find("tackler").get_text()][0], "type": event.get("type"), 'opponent': player_ids[event.get('player_id')][0] })
                            data[key][team_ids[event.find("tackler_team").get_text()][1]+"_short"] += 1
                        elif key == "takeons":
                            data[key][team_ids[event.get("other_team")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1, 'player': player_ids[event.get('other_player')][0], 'opponent': player_ids[event.get('player_id')][0], 'type': event.get('type') })
                            data[key][team_ids[event.get("other_team")][1]+"_short"] += 1
                        elif key == "blocked_events":
                            data[key][team_ids[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1, 'player': player_ids[event.get('player_id')][0], 'type': event.get('type') })
                            if event.find("shot") != None:
                                data[key][team_ids[event.get("team_id")][1]+"_detailed"][-1]['shot'] = bool(event.find("shot").get_text())
                            if event.find("headed") != None:
                                data[key][team_ids[event.get("team_id")][1]+"_detailed"][-1]['headed'] = bool(event.find("headed").get_text())
                            if event.get("type") == "blocked_shot" and event.has_attr("shot_player"):
                                data[key][team_ids[event.get("team_id")][1]+"_detailed"][-1]['shot_player'] = player_ids[event.get("shot_player")][0]
                            data[key][team_ids[event.get("team_id")][1]+"_short"] += 1
                        elif key == "fouls":
                            if event.find("otherplayer").get_text() == '0':
                                opponent = "-"
                            else:
                                opponent = player_ids[event.find("otherplayer").get_text()][0]  
                            data[key][team_ids[event.get("team")][1]+"_detailed"].append({'mins': int(event.get('mins'))+1, 'player': player_ids[event.get('player_id')][0], 'opponent': opponent })
                            data[key][team_ids[event.get("team")][1]+"_short"] += 1
                        elif key == "cards":
                            data[key][team_ids[event.get("team")][1]+"_detailed"].append({'mins': int(event.get('mins'))+1, 'player': player_ids[event.get('player_id')][0], 'card': event.find("card").get_text() })
                            data[key][team_ids[event.get("team")][1]+"_short"] += 1
                    except KeyError:
                        print("KEY ERROR: "+key+"; event mins: "+event.get("mins"))
                        print("Match date: "+processed_xml.find("squawka").get("date"))    
                        print("Teams: "+str(team_ids))       
        
        #putting data into excel spreadsheet                      
        squawka_datasheet = spreadsheet("C:/Users/HP10/AppData/Local/Programs/Python/Python35/Lib/site-packages/scrapy/projects/squawka/squawka/excel/squawka_data_"+str(self.page)+".xlsx", "Spain") 
        
        #a list of column names
        field_names = squawka_datasheet.get_data("Spain", self.fields_row, self.first_fields_column, 1, self.fields_amount, "row")

        #populating the spreadsheet with data
        for event_name in data.keys():
            print("NEW EVENT NAME: "+event_name)
            #if event_name not in ['date', 'home', 'away']: 
            if event_name in ['interceptions','clearances']:
                for detailed in data[event_name].keys(): #"home_detailed"/"away_detailed"/"home_total"/"away_total"
                    if detailed in ["home_detailed", "away_detailed"]:                        
                        for event in data[event_name][detailed]: #{'mins':'25', 'type': 'Possession', ...}
                            column_increment = 0 
                            for field_name in field_names:
                                if field_name in event.keys():    
                                    squawka_datasheet.set_data(str(event[field_name]), "Spain", self.input_row, self.first_fields_column+column_increment) #inputting 1 value at a time
                                    #print(field_name+": "+str(event[field_name]))
                                elif field_name == "total":
                                    squawka_datasheet.set_data(data[event_name][detailed[:4]+"_short"], "Spain", self.input_row, self.first_fields_column+column_increment)
                                    #print(field_name+": "+str(data[event_name][detailed[:4]+"_short"]))
                                elif field_name == "event":
                                    squawka_datasheet.set_data(event_name, "Spain", self.input_row, self.first_fields_column+column_increment)
                                    #print(field_name+": "+str(event_name))
                                elif field_name == "team":
                                    squawka_datasheet.set_data(data[detailed[:4]], "Spain", self.input_row, self.first_fields_column+column_increment)
                                    #print(field_name+": "+str(data[detailed[:4]]))
                                elif field_name in ["home", "away", "date"]:
                                    squawka_datasheet.set_data(data[field_name], "Spain", self.input_row, self.first_fields_column+column_increment)
                                    #print(field_name+": "+str(data[field_name]))
                                else:
                                    squawka_datasheet.set_data("-", "Spain", self.input_row, self.first_fields_column+column_increment)
                                    #print(field_name+": -")
                                column_increment += 1
                            self.input_row += 1
                            #print("=========NEXT EVENT==========")
        
        print("===============")
        squawka_datasheet.save()