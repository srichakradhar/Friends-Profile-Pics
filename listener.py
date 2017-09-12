
class Listener:
    """
    Listener is a API listener that can be extended by source specific listeners.
    """
    def __init__(self, source=None, source_type=None):
        """
        Constructor for Listener

        Parameters
        ----------
        source : str
            Source can be any websites from which data needs to be scraped/extracted.
        type : str
            Accepts one of these 2 types:
            - Api
            - Scraper
            Whether it is an Api or website content scraper

        Returns
        -------
        Listener
            Listener object

        """
        self.source = source
        self.type = source_type

    def get_posts(self, page_id):
        """
        Gets all the posts by page_id or group_id or user_id

        Parameters
        ----------
        page_id : str
            entity can be a fb page, twitter handle, youtube video.
            Anything that represents a collection of posts.

        Returns
        -------
        List
            List of posts from the page

        """
        raise NotImplementedError

    def get_comments(self, post_id):
        """
        Gets all the comments by post_id or tweet_id

        Parameters
        ----------
        post_id : str
            post can be a fb post, tweet, fb comment, youtube video.
            Anything that a user can post

        Returns
        -------
        List
            List of comments of the post

        """
        raise NotImplementedError

    def authenticate(self, access_id=None, access_secret=None):
        """
        Authenticates the website and returns the authentication token

        Parameters
        ----------
        access_id : str
            Access ID provided by the provider
        access_secret : str
            Access Secret provided by the provider

        Returns
        -------
        str
            authenticate token
        """
        raise NotImplementedError
