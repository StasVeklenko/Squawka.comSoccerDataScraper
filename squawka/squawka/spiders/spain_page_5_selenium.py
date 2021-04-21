import scrapy, time
from scrapy_splash import SplashRequest
from scrapy import Spider, Request
from scrapy.projects.squawka.squawka.excel import spreadsheet
from bs4 import BeautifulSoup
from collections import OrderedDict
from selenium import webdriver
import codecs, win_unicode_console

#REPEAT THIS WHOLE SPIDER 10 TIMES FOR EACH PAGE, SINCE THERE ARE 10 PAGES AND CAN'T DO THEM CONCURRENTLY
class MySpider(Spider):
    name = 'spain_page_5_selenium'
    page = 5
    url = 'http://www.squawka.com/match-results'
    match_links = list()
    fields_row = 3 #row of columns (fields) of table
    first_fields_column = 1 #column of a first field of table
    fields_amount = 14 #number of columns (fields)
    last_fields_column = first_fields_column + fields_amount - 1
    input_row = 4
    
    #scheme: do a request to initial url -> execute Lua script 'select La Liga, 2016/17 from the dropdown menus; collect all the links to pages with actual match data (for all pages, say 1 to 8 or however many there are)' -> after collection, go to each (one by one) 
    #start_requests() sets up the spanish parameters -> parser just goes to links
    def start_requests(self):
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
          
          assert(splash:go("http://www.squawka.com/match-results?pg="""+str(self.page)+""""))
          
          assert(splash:wait(3))
          
          return splash:html()
        end
        """  
        
        win_unicode_console.enable()
        
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
        
        #for xml pages - send just a usual scrapy request, not a Splash request
        
        match_script = """
        function main(splash, args)
          splash.private_mode_enabled = False
          
          assert(splash:go(args.url))
          
          assert(splash:wait(5))
          
          local roomID = splash:evaljs("chatClient.roomID")
          
          assert(splash:wait(1))
          
          splash:evaljs("document.querySelector('li#tab-overview').innerHTML = chatClient.roomID")
          
          assert(splash:wait(1)) 
        
          return splash:html()
        end
        """           
    
        for match_link in self.match_links:
                
            yield Request(match_link, self.parse_match_xml, meta = {
                'splash': {
                    'args': {
                        'lua_source': match_script
                        # optional; parameters passed to Splash HTTP API
                        # 'wait': 2,
                        # 'url' is prefilled from request url
                        # 'http_method' is set to 'POST' for POST requests
                        # 'body' is set to request body for POST requests
                    },
                    'endpoint' : '/execute'
                    #slot_policy=scrapy_splash.SlotPolicy.PER_DOMAIN,  # optional
                },
                'match_link': match_link
            }) 
        
    def parse_match_xml(self, response):
        link = "http://s3-irl-laliga.squawka.com/dp/ingame/"+response.xpath("//li[@id='tab-overview']/text()").extract()[0]
        chromeBrowser = webdriver.Chrome()
        chromeBrowser.set_page_load_timeout(30)
        chromeBrowser.set_script_timeout(30)
        chromeBrowser.get(link)
        time.sleep(3)
        page_source = chromeBrowser.page_source

        '''openpyxl API:
        opening workbook: workbook = openpyxl.load_workbook(workbook, keep_vba = True/False)
        opening worksheet: worksheet = workbook.get_sheet_by_name(worksheet_name)
        getting data: worksheet.cell(row,column).value
        setting data: worksheet.cell(row,column).value = data
        
        spreadsheet (which depends on openpyxl) API:
        __init__(workbook, worksheet, keep_vba=False)
        get_data(worksheet, row_start, column_start, incr_step, number_of_incrs, incr_along)
        set_data(data, worksheet, row_start, column_start, incr_step, incr_along, workbook = "", keep_vba=False) 
        save(workbook="", keep_vba=False)
        
        Directory change:
        os.chdir()
        
        https://stackoverflow.com/questions/35720323/scrapyjs-splash-click-controller-button
        https://stackoverflow.com/questions/35052999/using-scrapyjs-crawl-onclick-pages-by-splash
        https://github.com/scrapinghub/splash/issues/200
        https://github.com/scrapy-plugins/scrapy-splash/issues/27
        '''
        
        player_ids = {}
        team_ids = {}        
        processed_xml = BeautifulSoup(page_source, "xml") #.decode("utf-8")
        chromeBrowser.quit()       
        #converting str to dict: x = "{1: 'igor', 'stas': 'yo'}"; import ast; ast.literal_eval(x)
        
        #player ids
        for each in processed_xml.select("players player"):
            #player_ids[each.get("id")] = [codecs.escape_decode(each.find("name").get_text().encode("latin-1"))[0].decode("utf-8"), each.get("team_id")]     FOR SPLASH       
            player_ids[each.get("id")] = [each.find("name").get_text(), each.get("team_id")] 
        
        #team ids
        for each in processed_xml.select("data_panel game team"):
            if each.find("state").get_text() == "home":
                #home_team = codecs.escape_decode(each.find("short_name").get_text().encode("latin-1"))[0].decode("utf-8")     FOR SPLASH
                home_team = each.find("short_name").get_text()
            elif each.find("state").get_text() == "away": 
                #away_team = codecs.escape_decode(each.find("short_name").get_text().encode("latin-1"))[0].decode("utf-8")     FOR SPLASH
                away_team = each.find("short_name").get_text()
            #team_ids[each.get("id")] = [codecs.escape_decode(each.find("short_name").get_text().encode("latin-1"))[0].decode("utf-8"), each.find("state").get_text()]    FOR SPLASH
            team_ids[each.get("id")] = [each.find("short_name").get_text(), each.find("state").get_text()] 
        print(processed_xml.find("squawka").get("date"))
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
                    try:
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
        '''
        if response.meta.get("match_link") in self.match_links[:5]:
            squawka_datasheet = spreadsheet("C:/Users/HP10/AppData/Local/Programs/Python/Python35/Lib/site-packages/scrapy/projects/squawka/squawka/excel/squawka_data_"+str(self.page)+"_1 to 5.xlsx", "Spain") 
        elif response.meta.get("match_link") in self.match_links[15:20]:
            squawka_datasheet = spreadsheet("C:/Users/HP10/AppData/Local/Programs/Python/Python35/Lib/site-packages/scrapy/projects/squawka/squawka/excel/squawka_data_"+str(self.page)+"_16 to 20.xlsx", "Spain") 
        elif response.meta.get("match_link") in self.match_links[20:25]:
            squawka_datasheet = spreadsheet("C:/Users/HP10/AppData/Local/Programs/Python/Python35/Lib/site-packages/scrapy/projects/squawka/squawka/excel/squawka_data_"+str(self.page)+"_21 to 25.xlsx", "Spain") 
        '''
        squawka_datasheet = spreadsheet("C:/Users/HP10/AppData/Local/Programs/Python/Python35/Lib/site-packages/scrapy/projects/squawka/squawka/excel/squawka_data_"+str(self.page)+".xlsx", "Spain")     
        
        #PUTTING DATA INTO EXCEL SHEET                      
        
        #a list of column names
        field_names = squawka_datasheet.get_data("Spain", self.fields_row, self.first_fields_column, 1, self.fields_amount, "row")

        #populating the spreadsheet with data
        for event_name in data.keys(): #shots/clearances/headed duels/...
            print("NEW EVENT NAME: "+event_name)
            if event_name not in ['date', 'home', 'away']: 
                for detailed in data[event_name].keys(): #"home_detailed"/"away_detailed"/"home_total"/"away_total"
                    if detailed in ["home_detailed", "away_detailed"]:                        
                        for event in data[event_name][detailed]: #{'mins':'25', 'type': 'Possession', ...}
                            column_increment = 0 
                            for field_name in field_names:
                                if field_name in event.keys():    
                                    squawka_datasheet.set_data(str(event[field_name]), "Spain", self.input_row, self.first_fields_column+column_increment) #inputting 1 value at a time
                                    #if event_name == "interceptions":
                                    print(field_name+": "+str(event[field_name]))
                                elif field_name == "total":
                                    squawka_datasheet.set_data(data[event_name][detailed[:4]+"_short"], "Spain", self.input_row, self.first_fields_column+column_increment)
                                    #if event_name == "interceptions":
                                    print(field_name+": "+str(data[event_name][detailed[:4]+"_short"]))
                                elif field_name == "event":
                                    squawka_datasheet.set_data(event_name, "Spain", self.input_row, self.first_fields_column+column_increment)
                                    #if event_name == "interceptions":
                                    print(field_name+": "+str(event_name))
                                elif field_name == "team":
                                    squawka_datasheet.set_data(data[detailed[:4]], "Spain", self.input_row, self.first_fields_column+column_increment)
                                    #if event_name == "interceptions":
                                    print(field_name+": "+str(data[detailed[:4]]))
                                elif field_name in ["home", "away", "date"]:
                                    squawka_datasheet.set_data(data[field_name], "Spain", self.input_row, self.first_fields_column+column_increment)
                                    #if event_name == "interceptions":
                                    print(field_name+": "+str(data[field_name]))
                                else:
                                    squawka_datasheet.set_data("-", "Spain", self.input_row, self.first_fields_column+column_increment)
                                    #if event_name == "interceptions":
                                    print(str(field_name)+": -")
                                column_increment += 1
                            self.input_row += 1
                            #event_name == "interceptions":
                            print("=========NEXT EVENT==========")
        
        print("===============")
        squawka_datasheet.save()
        
        '''
        #recording number of last row to use it in the next data download
        max_len = 0        
        for key in data.keys():
            max_len = max(len(data[key]["home_detailed"]), len(data[key]["away_detailed"]), max_len)
        
        #populating the beginning columns with match number and team names
        for team_id in team_ids.keys():
            for i in range(max_len):
                squawka_datasheet.set_data(match_date, "Spain", self.input_row+i, 1) #PUT DATE OF MATCH AS FIRST COLUMN INSTEAD
                if team_ids[team_id][1] == "home":
                    squawka_datasheet.set_data(team_ids[team_id][0], "Spain", self.input_row+i, 2)
                elif team_ids[team_id][1] == "away":
                    squawka_datasheet.set_data(team_ids[team_id][0], "Spain", self.input_row+i, 3)        
        
        
        #incrementing the self.input_row 
        self.input_row = self.input_row + max_len   
        '''
        '''
        from scrapy.shell import inspect_response
        inspect_response(response, self)
        '''