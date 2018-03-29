import escpos.printer
import escpos.constants
import urllib.request
import json
import html
import math
import re
import xml.etree.ElementTree
import platform
import os
import json
import time

askan_pl = 5254
uni_bib = 7482
hassel = 7330

location_db = json.load(open('magdeburg-db.json'))


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
    if 337.5 <= bearing or bearing < 22.5:
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


def ask_nasa(number, max_journeys=10, download_infoline=True):
    base = "http://reiseauskunft.insa.de/bin/stboard.exe/dn?L=.vs_stb" \
           + "&L=.vs_stb.vs_stb&boardType=dep" \
           + "&date=" + time.strftime("%d.%m.%y", time.localtime()) \
           + "&time=" + time.strftime("%H:%M", time.localtime()) \
           + "&productsFilter=11111111&additionalTime=0&start=yes&requestType=0&" \
           + "maxJourneys=" + str(max_journeys) + "&input="
    con = urllib.request.urlopen(base + str(number)).read()[14:]
    con = html.unescape(con.decode())
    obj = json.loads(con)
    if download_infoline:
        for journey in obj['journey']:
            tinfoline_result = urllib.request.urlopen(journey['tinfoline']).read()
            tinfoline_result = html.unescape(tinfoline_result.decode())
            tinfoline_result = json.loads(tinfoline_result)
            journey['tinfoline_result'] = tinfoline_result
    with open("{:d}_{:.20g}.json".format(number, time.time()), 'w') as outfile:
        json.dump(obj, outfile)
    return obj


def ask_nasa_xml(number, max_journeys=10):
    base = "https://reiseauskunft.insa.de/bin/stboard.exe/dn?productsFilter=11111111&boardType=dep" \
           + "&disableEquivs=1" + "maxJourneys=" + str(max_journeys) \
           + "&date=" + time.strftime("%d.%m.%y", time.localtime()) \
           + "&time=" + time.strftime("%H:%M", time.localtime()) \
           + "&clientType=ANDROID&L=vs_java3&hcount=0&start=yes&input="
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
    with open("{:d}_{:.20g}.xml".format(number, time.time()), 'w') as outfile:
        outfile.write(con)
    return tree


def format_nasa_tree(tree, count=10):
    if tree.tag == 'Err':
        return tree.attrib['text']
    tree = list(tree)
    station_element = tree[0]
    tree.remove(station_element)
    assert station_element.tag == "St"
    station_name = station_element.attrib['name']
    station_nr = station_element.attrib['evaId']
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
        dirnr = elem.attrib['dirnr']

        direction = "(ER)"
        lat1 = int(location_db[station_nr]['lat']) * 1e-6
        lat2 = int(location_db[dirnr]['lat']) * 1e-6
        lon1 = int(location_db[station_nr]['lon']) * 1e-6
        lon2 = int(location_db[dirnr]['lon']) * 1e-6

        direction = "({:<2})".format(bearing_str(bearing(lat1, lon1, lat2, lon2)))
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
    station_nr = obj['stationEvaId']
    maxJ = obj['maxJ']  # count of journeys
    count = max(1, min(count - 1, maxJ - 1))
    i = 0
    for journey in obj['journey']:
        if i >= count:
            break
        if journey['rt'] and journey['rt']['status'] is not None:
            # print(journey)
            print("ERROR, Status is: " + journey['rt']['status'])
            count = (count + 1) % maxJ
            continue
        # read data from object
        product = journey['pr'][6:].strip()
        station = journey['st'][10:].strip()
        time = journey['ti'].strip()

        lat1 = location_db[station_nr]['lat']
        lon1 = location_db[station_nr]['lon']
        lat2 = lat1
        lon2 = lon1
        stops = journey['tinfoline_result']['stops']
        for stop in stops:
            if int(stop['y']) == lat1 and int(stop['x']) == lon1:
                lat2 = int(stops[int(stop['id']) + 1]['y'])
                lon2 = int(stops[int(stop['id']) + 1]['x'])
                location_db[station_nr]['bno'] = stop['bno']

        delay = "(+0)"

        lat1 = int(lat1) * 1e-6
        lat2 = int(lat2) * 1e-6
        lon1 = int(lon1) * 1e-6
        lon2 = int(lon2) * 1e-6

        direction = "({:<2})".format(bearing_str(bearing(lat1, lon1, lat2, lon2)))

        # add delay minutes if available
        if obj['journey'][i]['rt'] and obj['journey'][i]['rt']['dlm'] is not None \
                and int(obj['journey'][i]['rt']['dlm']) > 0:
            delay = "(+" + str(obj['journey'][i]['rt']['dlm']) + ")"

        # direction = ""
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

        i += 1
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
    device.text("{:^32}\n\n\n\n\n\n".format("FIN Telegram Gruppe"))


def print_n39_qr(device):
    device.qr("http://www.netz39.de", escpos.constants.QR_ECLEVEL_H, size=12)
    device.text("{:^32}\n\n\n\n\n\n".format("Netz39 Hackerspace"))


def print_lipsum(device):
    lipsum = "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.   \r\n\r\nDuis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat.   \r\n\r\nUt wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi.   \r\n\r\nNam liber tempor cum soluta nobis eleifend option congue nihil imperdiet doming id quod mazim placerat facer possim assum. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat.   \r\n\r\nDuis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis.   \r\n\r\nAt vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, At accusam aliquyam diam diam dolore dolores duo eirmod eos erat, et nonumy sed tempor et et invidunt justo labore Stet clita ea et gubergren, kasd magna no rebum. sanctus sea sed takimata ut vero voluptua. est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat.   \r\n\r\nConsetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus.   \r\n\r\nLorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.   \r\n\r\nDuis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat.   \r\n\r\nUt wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi.   \r\n\r\nNam liber tempor cum soluta nobis eleifend option congue nihil imperdiet doming id quod mazim placerat facer possim assum. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo"
    device.text(lipsum)


for nr in {uni_bib, askan_pl, hassel}:
    # print("asking for xml nr.:" + str(nr))
    tree = ask_nasa_xml(nr)
    # print("asking for json nr.:" + str(nr))
    obj = ask_nasa(nr)
    # print(format_nasa_tree(tree, 10))
    print(format_nasa_obj(obj, 10))

with open('magdeburg-db.json', 'w') as outfile:
    json.dump(location_db, outfile)
if platform.system() == 'Linux':
    p = escpos.printer.Usb(0x0456, 0x0808, in_ep=0x81, out_ep=0x03)
    # p = escpos.printer.File(u'/dev/usb/lp0')
else:
    p = escpos.printer.Dummy()  # does not work on windows :(

p.charcode("USA")
p.text(format_nasa_obj(ask_nasa(hassel, 20), 20))

# print_n39_qr(p)# print_cyberband(p,20)

# p.text("{:^32}".format("Mullvad Konto"))
# p.text("{:^32}\n\n\n\n\n\n".format("8441 6558 9986 4981"))

# p.image("/home/max/Bilder/Screenshot_20180327_015534.png")
p.text("\n\n\n\n\n\n")
