from listener import Listener
import facebook
from pymongo import MongoClient
from urlparse import parse_qs, urlparse


class FacebookListener(Listener):
    """
    FacebookListener is an API listener customized for facebook Graph API.
    """

    def __init__(self, access_token=None, nosqldb_host='localhost', nosqldb_port=27017):
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
        self.db = self.client.raw_data

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
            for comment in self.graph.get_all_connections(post_id, 'comments'):
                comments.insert_one(comment)
            print(str(comments.count()) + " comments saved to the database.")

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

    def get_posts(self, page_id):
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
        if self.access_token is not None:
            fb_page = self.graph.get_object(page_id)
            posts = self.db.posts
            posts_in_db = posts.count()

            fields_to_scrape = 'reactions.type(LOVE).limit(0).summary(total_count).as(reactions_love),' \
                               'reactions.type(WOW).limit(0).summary(total_count).as(reactions_wow),' \
                               'reactions.type(HAHA).limit(0).summary(total_count).as(reactions_haha),' \
                               'reactions.type(SAD).limit(0).summary(total_count).as(reactions_sad),' \
                               'reactions.type(ANGRY).limit(0).summary(total_count).as(reactions_angry),' \
                               'reactions.type(THANKFUL).limit(0).summary(total_count).as(reactions_thankful),' \
                               'message,created_time,description,link,name,permalink_url'

            while True:
                page = self.graph.get_connections(fb_page['id'], 'posts', fields=fields_to_scrape)
                next = page.get('paging', {}).get('next')
                posts.insert_many(page['data'])
                if not next:
                    print(str(posts.count() - posts_in_db) + " posts saved to the database.")
                    return
                args = parse_qs(urlparse(next).query)
                del args['access_token']
                print(str(len(page['data'])) + ' posts saved to the database.')
        else:
            raise ValueError("Not Authenticated.")