import jinja2
import logging
import requests
from bs4 import BeautifulSoup

logging.basicConfig(filename='post_server.log', level=logging.DEBUG)


def get_html(shop_thread_id):
    url = 'http://www.pathofexile.com/forum/view-thread/%s' % shop_thread_id
    html = requests.get(url).content
    html = html.replace(
        '/favicon.ico',
        'http://www.pathofexile.com/favicon.ico',
    )
    html = html.replace(
        '/js/lib/modernizr',
        'http://www.pathofexile.com/js/lib/modernizr',
    )
    return html


class PostIsolator(object):
    ''' Given a shop thread ID, regenerates the page HTML to only show the
    first post while retaining CSS and Javascript. Useful for embedding a
    single post in an iframe.
    '''
    def __init__(self, shop_thread_id):
        self.shop_thread_id = shop_thread_id
        self.jinja2_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                searchpath=[
                    'templates',
                    'forum/templates',
                    'pathofexile/forum/templates',
                ]
            )
        )
        self.thread_html = get_html(self.shop_thread_id)  # original page
        self.soup = BeautifulSoup(self.thread_html)
        self.head_tag = self.soup.find('head')
        try:
            self.first_post = self.find_first_post()
            self.javascript = self.find_javascript()
            self.html = self.generate_html()  # regenerated page
        except Exception as e:
            logging.exception(e.message)
            self.html = self.jinja2_env.get_template('invalid.html').render(
                head_tag=str(self.head_tag),
            )

    def find_first_post(self):
        ''' Finds the table of class "forumPostListTable", isolates the first
        row, and then isolates the first column in that row. This leaves only
        the first post of a thread, without the sidebar.
        '''
        attrs = {'class': 'forumTable forumPostListTable'}
        post_table = self.soup.find('table', attrs=attrs)
        first_post = post_table.find('tr')
        first_post_body = first_post.find('td')
        return first_post_body

    def find_javascript(self):
        ''' Finds all <script type='text/javascript'> tags in the page, and
        filters out the ones which are already in the <head> tag (and the ones
        which are manually specified below).

        5 is set manually, because we have 2 <script> fields in the <head>
        section, and 3 more hardcoded in the jinja2 template.

        This needs some work, to make sure we're picking up javascript in the
        right way. Counting manually isn't very resilient to upstream changes.
        Also need to account for <script src=""> elements, which have no text
        and therefore do nothing when converted to a string.
        '''
        js = self.soup.find_all('script', type='text/javascript')
        new_js = js[5:]
        return ''.join([str(j) for j in new_js])

    def generate_html(self):
        ''' Passes the head tag, first post, and javascript into a jinja2
        template to be rendered into a new, complete HTML page.
        '''
        template = self.jinja2_env.get_template('post.html')
        return template.render(
            head_tag=str(self.head_tag),
            first_post=str(self.first_post),
            javascript=self.javascript,
        )
