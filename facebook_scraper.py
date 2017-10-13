from listener import Listener
from facebook_listener import FacebookListener

# listener_ = Listener("https://www.facebook.com", "API")
fb_listener = FacebookListener()
fb_listener.authenticate('668324820013751', '95cfde262f8f3c9fa10b95d5fa2ff8e3')
# posts = fb_listener.get_posts('free.code.camp.hyderabad')
# comments = fb_listener.get_comments('2046682258890974_2209152715977260')
f = open('fb_ids_2k.txt', 'r')
try:
    for fb_id in f.readlines():
        fb_listener.get_posts(fb_id.strip())
except:
    print("Scraping Aborted.")
finally:
    f.close()
