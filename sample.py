import ledje
import time
import datetime
import requests
import lxml.html
from textwrap import wrap

display = ledje.Ledje()


print(display._send_command(1, 'G        '))
print(display.configure(1))
print(display.start_programming_mode(1))
print(display.schedule(1))
curtime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
regeltjes_tekst = (display.strftime('%d-%m      L_I_C_H_T_K_R_A_N_T_      %H:%M:%S'), 'laatst geupdatet {}'.format(curtime))
print(display.add_slide(text=regeltjes_tekst, addr=1, program_number=1, page_number=1, appear_effect=1, disappear_effect=1, display_seconds=99))
print(display.stop_programming_mode(1))

print(display._send_command(2, 'G        '))
print(display.configure(2))
print(display.start_programming_mode(2))
print(display.schedule(2))

page_number = 1
# WEERSVOORSPELLING NOS
response = requests.get('https://nos.nl/weer')
tree = lxml.html.fromstring(response.text)
weer_tekstje = wrap(str(tree.xpath("/html/body/main/div/section[1]/div/div/div/div[1]/p")[0].text_content()), 45)

weer_tekstje_split = [weer_tekstje[i:i+5] for i in range(0,len(weer_tekstje),5)]
# maximaal 5 regels ivm header
header = "W_e_e_r_ (nos.nl/weer) ({}/{})"
for idx, split in enumerate(weer_tekstje_split):
    split_slide_text = [header.format(idx + 1, len(weer_tekstje_split))] + split
    print(display.add_slide(text=split_slide_text, addr=2, program_number=1, page_number=page_number, appear_effect=3, disappear_effect=6, display_seconds=10))
    page_number += 1
# /WEERSVOORSPELLING NOS

print(display.stop_programming_mode(2))
