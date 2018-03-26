import escpos.printer
import urllib.request
import json
import html
import math
import re
import xml.etree.ElementTree
askan_pl = 5254
uni_bib = 7482
hassel = 7330


# https://www.movable-type.co.uk/scripts/latlong.html
def bearing(lat1, lon1, lat2, lon2):
    lat1 *= (math.pi/180.0)
    lat2 *= (math.pi/180.0)
    d_lon = (lon2 - lon1) * (math.pi/180.0)
    y = math.sin(d_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
    b = math.atan2(y, x)
    return (b * 180.0 / math.pi) % 360


def bearing_str(bearing):
    bearing = bearing % 360
    if 337.5 <= bearing < 22.5:
        return "N"
    if 22.5 <= bearing < 67.5:
        return "NO"
    if 67.5 <= bearing < 112.5:
        return "O"
    if 112.5 <= bearing < 157.5:
        return "SO"
    if 157.5 <= bearing < 202.5:
        return "S"
    if 202.5 <= bearing < 247.5:
        return "SW"
    if 247.5 <= bearing < 292.5:
        return "W"
    if 292.5 <= bearing < 337.5:
        return "NW"


def ask_nasa(number):
    base = "http://reiseauskunft.insa.de/bin/stboard.exe/dn?L=.vs_stb&L=.vs_stb.vs_stb&boardType=dep&selectDate=today&productsFilter=0000011111&additionalTime=0&start=yes&requestType=0&maxJourneys=200&input="
    con = urllib.request.urlopen(base + str(number)).read()[14:]
    con = html.unescape(con.decode())
    obj = json.loads(con)
    return obj


def ask_nasa_xml(number):
    base = "https://reiseauskunft.insa.de/bin/stboard.exe/dn?productsFilter=11111111&boardType=dep&disableEquivs=1&maxJourneys=200&selectdate=today&clientType=ANDROID&L=vs_java3&hcount=0&start=yes&input="
    con = urllib.request.urlopen(base + str(number)).read()
    con = str(con.decode())
    regex = re.compile("<HIMMessage.*?<\/Journey>", re.DOTALL | re.MULTILINE)
    con = regex.sub("</Journey>", con)
    '''
    con = con.replace("<b>", " ")
    con = con.replace("</b>", " ")
    con = con.replace("<u>", " ")
    con = con.replace("</u>", " ")
    con = con.replace("<i>", " ")
    con = con.replace("</i>", " ")
    con = con.replace("<br />", " ")
    con = con.replace(" ->", " &#x2192")
    con = con.replace(" <-", " &#x2190")
    con = con.replace(" <> ", " &#x2194 ")
    con = con.replace("\"Florian Geyer\"", "Florian Geyer")
    '''
    con = html.unescape(con)
    tree = xml.etree.ElementTree.fromstring(con)
    for elem in list(tree):
        print(elem.attrib)
    return tree


def format_nasa_tree(tree, count=30):
    station_element = tree.pop()
    station_name = station_element['name']
    station_name = station_name[station_name.find(',') + 1:] #cuts "Magdeburg, "
    i = 0
    for elem in tree:
        i += 1
        if i <= count:
            break




def format_nasa_obj(obj, count=30):
    station_name = str(obj['stationName'])
    station_name = station_name[station_name.find(',') + 1:]
    result = "{:^32}\n".format(station_name)
    # result += "Nr Name           Zeit(Richtung)\n"

    maxJ = obj['maxJ']  # count of journeys
    count = max(1, min(count, maxJ))
    i = 0
    while i < count:
        i += 1

        if obj['journey'][i]['rt'] and obj['journey'][i]['rt']['status'] is not None:
            print("ERROR, Status is: " + obj['journey'][i]['rt']['status'])
            count += 1
            continue
        # read data from object
        product = obj['journey'][i]['pr'][6:].strip()
        station = obj['journey'][i]['st'][10:].strip()
        time = obj['journey'][i]['ti'].strip()
        '''
        delay = "(+0)"

        # add delay minutes if available
        if obj['journey'][i]['rt'] and obj['journey'][i]['rt']['dlm'] is not None \
                and int(obj['journey'][i]['rt']['dlm']) > 0:
            delay = "(+" + str(obj['journey'][i]['rt']['dlm']) + ")"
        '''
        direction = "(NO)"
        # calculate maximum length of station name
        available_name_len = 32 - (2 + 2 + len(time) + len(direction))

        # shorten station name
        station = cut_at(station, ',')
        station = cut_at(station, '(')
        station = station[:available_name_len]

        # format string
        string = "{:<2} {:<{l}} {}{}".format(product, station, time, direction, l=available_name_len)
        # print(string)
        result += string + '\n'
    return result


def cut_at(string, c):
    location = string.find(c)
    if location > -1:
        return string[:location].strip()
    else:
        return string

#b = bearing(52.140357, 11.646514, 52.137912, 11.650973)
#print(bearing_str(b))

# askNASA(hassel)
obj = ask_nasa(uni_bib)
tree=ask_nasa_xml(uni_bib)
print(format_nasa_obj(obj))
# print("\n\n")
# askNASA(askanischerPlatz)
# Adapt to your needs
p = escpos.printer.File(u'/dev/usb/lp1')

# Print software and then hardware barcode with the same content
p.charcode("USA")
# for i in range(1, 30):
#    p.image("/home/max/Dropbox/cyber.png")
#    p.text("\n\n\n\n\n\n")
# for code in range(1,100):
#    p.barcode(str(code),bc='CODE39')
# lipsum="Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.   \r\n\r\nDuis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat.   \r\n\r\nUt wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi.   \r\n\r\nNam liber tempor cum soluta nobis eleifend option congue nihil imperdiet doming id quod mazim placerat facer possim assum. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat.   \r\n\r\nDuis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis.   \r\n\r\nAt vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, At accusam aliquyam diam diam dolore dolores duo eirmod eos erat, et nonumy sed tempor et et invidunt justo labore Stet clita ea et gubergren, kasd magna no rebum. sanctus sea sed takimata ut vero voluptua. est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat.   \r\n\r\nConsetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus.   \r\n\r\nLorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.   \r\n\r\nDuis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat.   \r\n\r\nUt wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi.   \r\n\r\nNam liber tempor cum soluta nobis eleifend option congue nihil imperdiet doming id quod mazim placerat facer possim assum. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo"
# p.text(lipsum)
# p.qr("https://t.me/joinchat/BLReWz2rFi4LsL_uwM1yZA", constants.QR_ECLEVEL_H, size=9)
# p.text("\n         FIN Telegram Gruppe\n\n\n\n\n\n")
# p.text('People in general do not\nwillingly read if they have\nanything else to amuse them.\n                -- S. Johnson\n\n')
# p.text("\n\n\n\n\n\n")
