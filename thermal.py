import escpos.printer
import escpos.constants
import urllib.request
import json
import html
import math
import re
import xml.etree.ElementTree
import platform

askan_pl = 5254
uni_bib = 7482
hassel = 7330


# https://www.movable-type.co.uk/scripts/latlong.html
def bearing(lat1, lon1, lat2, lon2):
    lat1 *= (math.pi / 180.0)
    lat2 *= (math.pi / 180.0)
    d_lon = (lon2 - lon1) * (math.pi / 180.0)
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
    base = "http://reiseauskunft.insa.de/bin/stboard.exe/dn?L=.vs_stb"
    options = "&L=.vs_stb.vs_stb&boardType=dep&selectDate=today&productsFilter=0000011111&additionalTime=0&start=yes&requestType=0&maxJourneys=200&input="
    con = urllib.request.urlopen(base + options + str(number)).read()[14:]
    con = html.unescape(con.decode())
    obj = json.loads(con)
    return obj


def ask_nasa_xml(number):
    base = "https://reiseauskunft.insa.de/bin/stboard.exe/dn?productsFilter=11111111&boardType=dep&disableEquivs=1&maxJourneys=200&selectdate=today&clientType=ANDROID&L=vs_java3&hcount=0&start=yes&input="
    con = urllib.request.urlopen(base + str(number)).read()
    con = str(con.decode())
    regex = re.compile("<HIMMessage.*?<\/Journey>", re.DOTALL | re.MULTILINE)
    con = regex.sub("</Journey>", con)

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

    con = html.unescape(con)
    tree = xml.etree.ElementTree.fromstring(con)
    return tree


def format_nasa_tree(tree, count=10):
    tree = list(tree)
    station_element = tree[0]
    tree.remove(station_element)
    assert station_element.tag == "St"
    station_name = station_element.attrib['name']
    station_name = station_name[station_name.find(',') + 2:]  # cuts "Magdeburg, "
    result = "{:^32}\n".format(station_name)
    i = 0
    for elem in tree:
        i += 1
        if i >= count:
            break
        if elem.attrib['delay'] == 'cancel':
            print(elem)
            count += 1
            continue
        product = elem.attrib['hafasname'][6:]
        station = elem.attrib['dir']
        time = elem.attrib['fpTime']

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


def format_nasa_obj(obj, count=10):
    station_name = str(obj['stationName'])
    station_name = station_name[station_name.find(',') + 2:]
    result = "{:^32}\n".format(station_name)
    # result += "Nr Name           Zeit(Richtung)\n"

    maxJ = obj['maxJ']  # count of journeys
    count = max(1, min(count - 1, maxJ - 1))
    i = 0
    for journey in obj['journey']:
        i += 1
        if i >= count:
            break
        if journey['rt'] and journey['rt']['status'] is not None:
            print(journey)
            print("ERROR, Status is: " + journey['rt']['status'])
            count += 1
            continue
        # read data from object
        product = journey['pr'][6:].strip()
        station = journey['st'][10:].strip()
        time = journey['ti'].strip()
        '''
        delay = "(+0)"

        # add delay minutes if available
        if obj['journey'][i]['rt'] and obj['journey'][i]['rt']['dlm'] is not None \
                and int(obj['journey'][i]['rt']['dlm']) > 0:
            delay = "(+" + str(obj['journey'][i]['rt']['dlm']) + ")"
        '''
        direction = ""
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


def print_cyberband(device, count):
    for i in range(1, count):
        device.image("cyber.png")
        device.text("\n\n\n\n\n\n")


def print_fin_telegram_qr(device):
    device.qr("https://t.me/joinchat/BLReWz2rFi4LsL_uwM1yZA", escpos.constants.QR_ECLEVEL_H, size=9)
    device.text("{:^32\n\n\n\n\n\n".format("FIN Telegram Gruppe"))


def print_lipsum(device):
    lipsum = "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.   \r\n\r\nDuis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat.   \r\n\r\nUt wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi.   \r\n\r\nNam liber tempor cum soluta nobis eleifend option congue nihil imperdiet doming id quod mazim placerat facer possim assum. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat.   \r\n\r\nDuis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis.   \r\n\r\nAt vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, At accusam aliquyam diam diam dolore dolores duo eirmod eos erat, et nonumy sed tempor et et invidunt justo labore Stet clita ea et gubergren, kasd magna no rebum. sanctus sea sed takimata ut vero voluptua. est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat.   \r\n\r\nConsetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus.   \r\n\r\nLorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.   \r\n\r\nDuis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat.   \r\n\r\nUt wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi.   \r\n\r\nNam liber tempor cum soluta nobis eleifend option congue nihil imperdiet doming id quod mazim placerat facer possim assum. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo"
    device.text(lipsum)


# b = bearing(52.140357, 11.646514, 52.137912, 11.650973)
# print(bearing_str(b))
obj = ask_nasa(uni_bib)
print(format_nasa_obj(obj, 200))
tree = ask_nasa_xml(uni_bib)
print(format_nasa_tree(tree, 200))

if platform.system() == 'Linux':
    p = escpos.printer.File(u'/dev/usb/lp1')
else:
    p = escpos.printer.Dummy()  # does not work on windows :(
    # p = escpos.printer.Usb(0x0456, 0x0808, in_ep=0x81, out_ep=0x03)

p.charcode("USA")

print_fin_telegram_qr(p)