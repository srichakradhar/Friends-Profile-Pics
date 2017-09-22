from listener import Listener
import facebook
import pymongo
from pymongo import MongoClient
from urlparse import parse_qs, urlparse
import time
from datetime import datetime
import threading


class FacebookListener(Listener):
    """
    FacebookListener is an API listener customized for facebook Graph API.
    """

    def __init__(self, access_token=None, nosqldb_host='localhost', nosqldb_port=27017, nosqldb_name='facebook'):
        """
        Constructor for FacebookListener

        Parameters
        ----------
        access_token : str (optional)
            Initializes the listener with access_token
            Access token is required to make api calls. 
            A temporary access token can be obtained here: https://developers.facebook.com/tools/explorer/
            Instead of access_token, authenticate can be used with app id and secret 
        host: MongoDB host address
        port: port on which MongoDB runs

        Returns
        -------
        FacebookListener
            FacebookListener object

        """
        Listener.__init__(self, "https://www.facebook.com", "API")
        if access_token is None:
            self.access_token = None
        else:
            self.access_token = access_token

        self.client = MongoClient(nosqldb_host, nosqldb_port)
        self.db = self.client[nosqldb_name]

    def get_comments(self, post_id):
        """
        Get all the comments for a post

        Parameters
        ----------
        post_id : str
            it is found in the response from get_posts
            e.g.: 216311481960_10154158548531961
            you can create it from the facebook post url by concatenating user id and the post id
            For this particular post, BillGates page user id is 216311481960 and 
            https://www.facebook.com/BillGates/posts/10154158548531961 is the post url
        
        Returns
        -------
        Iterator:
            Iterator for posts
            error: Authentication error
        """
        if self.access_token is not None:
            comments = self.db.comments
            comments_in_db = comments.count()
            for comment in self.graph.get_connections(post_id, 'comments', fields='comments', summary=1):
                comments.insert_one(comment)
            print(str(comments.count() - comments_in_db) + " comments saved to the database.")

        else:
            raise ValueError("Not Authenticated.")

    def update_comments(self, post_id):
        # TODO: Update the comments after the latest date in the database
        pass

    def authenticate(self, access_id=None, access_secret=None):
        """
        Get the access_token from app_id and secret

        Parameters
        ----------
        access_id : str
            App ID mentioned in the app dashboard
            e.g.: https://developers.facebook.com/apps/<your_app_id>/dashboard/
            
        access_secret: str
            App Secret mentioned in the app dashboard

        Returns
        -------
        None
            error: Authentication error
        """
        try:
            self.access_token = facebook.GraphAPI().get_app_access_token(access_id, access_secret)
            self.graph = facebook.GraphAPI(access_token=self.access_token, version='2.10')
            return self.access_token
        except Exception as e:
            self.access_token = None
            return {'error': "Authentication Error: " + str(e)}

    def get_posts(self, page_id, since='', until=''):
        """
        Get all the posts for a page or a group

        Parameters
        ----------
        page_id : str
            The unique id of the page or the group to be scraped.
            page_id: BillGates
            https://www.facebook.com/BillGates/
            group_id: free.code.camp.hyderabad
            https://www.facebook.com/groups/free.code.camp.hyderabad/

        Returns
        -------
        Iterator:
            Iterator for posts
            error: Authentication error
        """
        page_obj = None
        page = None
        new_page = False
        limit = 100
        try:
            if self.access_token is not None:
                self.post_ids = []
                fb_page = self.graph.get_object(page_id)

                # if page not exists create a new entry
                page_obj = self.db.pages.find_one({'id': fb_page['id']})
                if not page_obj:
                    new_page = True
                    page_obj = self.db.pages.find_one({'_id': self.create_page(fb_page['id']).inserted_id})

                posts = self.db.posts
                posts_in_db = posts.count()

                fields_to_scrape = 'message,created_time,place,type,permalink_url,' \
                                   'comments.limit(0).summary(total_count),shares,' \
                                   'reactions.type(LIKE).limit(0).summary(total_count).as(nlikes),' \
                                   'reactions.type(LOVE).limit(0).summary(total_count).as(nloves),' \
                                   'reactions.type(WOW).limit(0).summary(total_count).as(nwows),' \
                                   'reactions.type(HAHA).limit(0).summary(total_count).as(nhahas),' \
                                   'reactions.type(SAD).limit(0).summary(total_count).as(nsads),' \
                                   'reactions.type(ANGRY).limit(0).summary(total_count).as(nangrys),' \
                                   'reactions.type(THANKFUL).limit(0).summary(total_count).as(nthankfuls)'
                # 'comments.summary(1){comments.summary(1)}' (subquery for comments)

                # if not scraping for the first time, scrape until the oldest date
                if not new_page:
                    print(page_id + " has " + str(posts_in_db) + " posts.")
                    oldest_post = self.db.posts.find().sort('created_time', pymongo.ASCENDING).limit(1)
                    if oldest_post.count() > 0:
                        oldest_post_date = oldest_post[0]['created_time']
                        until = "%.0f" % time.mktime(
                            datetime.strptime(oldest_post_date, '%Y-%m-%dT%H:%M:%S+0000').timetuple())

                # comments_thread = threading.Thread(target=self.get_comments)
                # comments_thread.daemon = True
                # comments_thread.start()

                print("Scraping posts for " + page_id)
                count = 0
                args = {'fields': fields_to_scrape, 'limit': limit, 'until': until}
                while True:
                    count += 1
                    page = self.graph.get_connections(fb_page['id'], 'posts', **args)
                    if len(page['data']) > 0:
                        print(count, "date: ", page['data'][0]['created_time'])
                        posts.insert_many(page['data'])

                        # latest date is the first entry in the response
                        if new_page and count == 1:
                            self.db.pages.update_one({'_id': page_obj['_id']},
                                                     {'$set': {'latest_date': page['data'][0]['created_time']}})
                    else:
                        print("No new posts for " + page_id)
                    next = page.get('paging', {}).get('next')
                    # self.post_ids += [post_obj['id'] for post_obj in page['data']]
                    if not next:
                        print(str(posts.count() - posts_in_db) + " posts added to the database. Now, we have " + str(
                            posts.count()) + " Posts")
                        return
                    args = parse_qs(urlparse(next).query)
                    args['fields'] = fields_to_scrape
                    args['limit'] = limit
                    args['since'] = since
                    args['until'] = until
                    del args['access_token']
                    # print(str(len(page['data'])) + ' posts saved to the database.')
            else:
                raise ValueError("Not Authenticated.")

        except KeyboardInterrupt:
            print('Stopped scraping posts and started scraping comments for the posts scraped now.')
            if page_obj and page:
                self.db.pages.update_one({'_id': page_obj['_id']},
                                         {'$set': {'error_date': page['data'][-1]['created_time']}})
                # self.get_comments()
        except facebook.GraphAPIError as fbge:
            print("Failed to scrape posts for " + page_id + ".\n" + str(fbge))
            if page_obj and page:
                self.db.pages.update_one({'_id': page_obj['_id']},
                                         {'$set': {'error_date': page['data'][-1]['created_time']}})

    def create_page(self, page_id):
        page_meta = 'id,name,about,global_brand_page_name,category,description,display_subtext,emails,' \
                    'mission,is_community_page,verification_status,overall_star_rating,rating_count,' \
                    'affiliation,awards,best_page,bio,birthday,category_list,company_overview,contact_address,' \
                    'country_page_likes,culinary_team,current_location,description_html,engagement,fan_count,' \
                    'founded,general_info,general_manager,name_with_location_descriptor,new_like_count,phone,' \
                    'place_type,products,website,username,single_line_address,store_location_descriptor,hours'

        group_meta = 'id,name,description,email,owner,parent,privacy,updated_time'

        details = None

        try:
            details = self.graph.get_connections(page_id, '', fields=page_meta)
            print(page_id + " is a page.")
        except:
            try:
                details = self.graph.get_connections(page_id, '', fields=group_meta)
                print(page_id + " is a group.")
            except:
                print("ID provided is neither a Page nor a Group.")

        cursor = None

        if details:
            cursor = self.db.pages.insert_one(details)

        return cursor
