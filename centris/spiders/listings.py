from scrapy_splash import SplashRequest
from scrapy.selector import Selector
import scrapy
import json


class ListingsSpider(scrapy.Spider):

    name = "listings"
    allowed_domains = ["www.centris.ca"]
    position = {"startPosition": 0}

    http_user = "user"
    http_pass = "userpass"

    script = """
            function main(splash, args)
  
              splash:on_request(function(request)
                  if request.url:find("css") then
                   request.abort()
                  end		
              end)
            
              splash.private_mode_enabled = false
              splash.images_enabled = false
              splash.js_enabled = false
            
              req_headers = {
                ["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36",
                ["Accept-Language"] = "en-GB,en;q=0.9,en-US;q=0.8,es;q=0.7"
              }
            
              splash:set_custom_headers(req_headers)
            
              assert(splash:go(args.url))
              assert(splash:wait(1.5))
              
              splash:set_viewport_full()
              return splash:html()
              
            end
        """

    def start_requests(self):

        yield scrapy.Request(
            url="https://www.centris.ca/UserContext/Lock",
            method="POST",
            headers={
                "x-requested-with": "XMLHttpRequest",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"

            },
            body=json.dumps({"uc": 0}),
            callback=self.generate_uck
        )

    def generate_uck(self, response):

        uck = response.text

        query = {
            "query": {
                "UseGeographyShapes": 0,
                "Filters": [
                    {
                        "MatchType": "CityDistrictAll",
                        "Text": "Montréal (All boroughs)",
                        "Id": 5
                    }
                ],
                "FieldsValues": [
                    {
                        "fieldId": "CityDistrictAll",
                        "value": 5,
                        "fieldConditionId": "",
                        "valueConditionId": ""
                    },
                    {
                        "fieldId": "Category",
                        "value": "Residential",
                        "fieldConditionId": "",
                        "valueConditionId": ""
                    },
                    {
                        "fieldId": "SellingType",
                        "value": "Rent",
                        "fieldConditionId": "",
                        "valueConditionId": ""
                    },
                    {
                        "fieldId": "LandArea",
                        "value": "SquareFeet",
                        "fieldConditionId": "IsLandArea",
                        "valueConditionId": ""
                    },
                    {
                        "fieldId": "RentPrice",
                        "value": 0,
                        "fieldConditionId": "ForRent",
                        "valueConditionId": ""
                    },
                    {
                        "fieldId": "RentPrice",
                        "value": 1500,
                        "fieldConditionId": "ForRent",
                        "valueConditionId": ""
                    }
                ]
            },
            "isHomePage": True
        }

        yield scrapy.Request(
            url="https://www.centris.ca/property/UpdateQuery",
            method="POST",
            body=json.dumps(obj=query),
            headers={
                 "Content-Type": "application/json",
                 "x-requested-with": "XMLHttpRequest",
                 "x-centris-uc": 0,
                 "x-centris-uck": uck,
                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
             },
            callback=self.update_query,
            meta={"suck": uck}
        )

    def update_query(self, response):

        fuck = response.request.meta["suck"]

        yield scrapy.Request(
            url="https://www.centris.ca/Property/GetInscriptions",
            method="POST",
            body=json.dumps(self.position),
            headers={
                "Content-Type": "application/json",
                "x-requested-with": "XMLHttpRequest",
                "x-centris-uc": 0,
                "x-centris-uck": fuck,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
            },
            callback=self.parse,
            meta={"duck": fuck}
        )

    def parse(self, response):

        buck = response.request.meta["duck"]
        resp = json.loads(s=response.body)
        html = resp.get("d").get("Result").get("html")

        # with open(file="index.html", mode="w") as f:
        #     f.write(html)

        sel = Selector(text=html)
        apts = sel.xpath("//div[contains(@class, 'property-thumbnail-item')]")

        for apt in apts:

            relative_url = apt.xpath(".//div[@class='shell']/a/@href").get()
            absolute_url = f"https://www.centris.ca/en{relative_url[3:]}"
            price = apt.xpath("normalize-space(.//div//div[@class='price']/span[1]//text())").get()

            yield SplashRequest(
                url=absolute_url,
                callback=self.parse_summary,
                endpoint="execute",
                args={
                    "lua_source": self.script
                },
                meta={
                    "cat": apt.xpath("normalize-space(.//span[@class='category']//div/text())").get(),
                    "fea": apt.xpath("normalize-space(.//div[@class='cac']/text())").get(),
                    "pri": price.replace("\xa0", ""),
                    "cit": apt.xpath(".//span[@class='address']/div[2]//text()").get(),
                    "link": absolute_url
                }
            )

        count = resp.get("d").get("Result").get("count")
        increment = resp.get("d").get("Result").get("inscNumberPerPage")

        if self.position["startPosition"] <= count:

            self.position["startPosition"] += increment

            yield scrapy.Request(
                url="https://www.centris.ca/Property/GetInscriptions",
                method="POST",
                body=json.dumps(self.position),
                headers={
                    "Content-Type": "application/json",
                    "x-requested-with": "XMLHttpRequest",
                    "x-centris-uc": 0,
                    "x-centris-uck": buck,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
                },
                callback=self.parse,
                meta={"duck": buck}
            )

    def parse_summary(self, response):

        yield {
            "address": response.xpath("(//h2[@itemprop='address']/text())[1]").get(),
            "description": response.xpath("normalize-space(//div[@itemprop='description']/text())").get(),
            "features": response.request.meta["fea"],
            "price": response.request.meta["pri"],
            "city": response.request.meta["cit"],
            "url": response.request.meta["link"],
            "category": response.request.meta["cat"]
        }
