from bs4 import BeautifulSoup
import operator
import urllib
from http import cookiejar
from urllib import request, parse
import re
from async_promises import Promise
import time

cj = cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
urllib.request.install_opener(opener)

word_list = []
for_my_program_url = "https://waterlooworks.uwaterloo.ca/myAccount/co-op/coop-postings.htm"
# for_my_program_url = "https://waterlooworks.uwaterloo.ca/myAccount/hire-waterloo/other-jobs/jobs-postings.htm"


def add_word(words):
    global word_list
    for word in words:
        clean_word = clean_up_word(word.lower())
        if len(clean_word) > 0:
            word_list.append(clean_word)


def clean_up_word(word):
    if re.search("\<.+?\>", word) is not None:
        word = re.sub("\<.+?\>", " ", word)
        add_word(word.split(" "))
        return ""
    if re.search("\/", word) is not None:
        word = re.sub("\/", " ", word)
        add_word(word.split(" "))
        return ""
    word = word.strip()
    word = word.replace("\n", "")
    word = word.replace("\r", "")
    word = word.replace("\t", "")
    symbols = ".!@$%^&*()_{}|:\"?><-=][';/,']"
    for i in range(0, len(symbols)):
        word = word.replace(symbols[i], "")

    return word


def create_dictionary():
    global word_list
    word_count = {}
    for word in word_list:
        if word in word_count:
            word_count[word] += 1
        else:
            word_count[word] = 1
    with open('dictionary.txt', 'w', encoding='UTF-8') as f:
        for key, value in sorted(word_count.items(), key=operator.itemgetter(1), reverse=True):
            # 1 means sort by values, 0 will means sorted by keys
            f.write(str(key) + "\t\t" + str(value) + "\n")


def get_program_detail_content_promise(page_counter, counter, link):
    def get_program_detail(resolve, reject):
        # print(str(page_counter * 100 - 100 + counter + 1) + " Getting Program Lists")
        program_form_page = urllib.request.urlopen(for_my_program_url + link)
        program_form_content = program_form_page.read()

        # it get another form and we need to submit it
        input_form_data = {}
        input_soup = BeautifulSoup(program_form_content, "html.parser")
        for form_input in input_soup.findAll('input'):
            input_tokens = re.search('\<input name=\"(.*?)\" type=\"hidden\" value\=\"(.*?)\"\/\>',
                                     str(form_input))
            input_form_data[input_tokens.group(1)] = input_tokens.group(2)

        print(str(page_counter * 100 - 100 + counter + 1) + " Acquiring Program Information")
        complete_form_data = urllib.parse.urlencode(input_form_data).encode()
        program_detail_page = urllib.request.urlopen(for_my_program_url, complete_form_data)
        program_detail_content = program_detail_page.read()

        print(str(page_counter * 100 - 100 + counter + 1) + " Gathering Program Information")
        project_category = BeautifulSoup(program_detail_content, "html.parser")

        info = ""
        for project_info in project_category.findAll('td', attrs={"width": "75%"}):
            info_tokens = re.search('\<td width=\"75%\"\>([\w\W]+?)\<\/td\>', str(project_info))
            if info_tokens is not None:
                # add_word(info_tokens.group(1).split(" "))
                info += info_tokens.group(1).lstrip().rstrip()

        resolve(info)

    return Promise(get_program_detail)


def get_all_page_program_detail_content_promise(program_list_page_token, counter, first_page_content):
    def get_all_page_program_detail(resolve, reject):
        print("Getting Program Lists " + str(counter))
        if counter != 1:
            selected_program_list_data = urllib.parse.urlencode(
                {
                    'action': program_list_page_token,
                    'orderBy': '',
                    'oldOrderBy': '',
                    'sortDirection': 'Forward',
                    'keyword': '',
                    'searchBy': 'jobViewCountCurrentTerm',
                    'searchType': '',
                    'initialSearchAction': 'displayViewedJobs',
                    'postings': 'infoForPostings',
                    'page': str(counter),
                    'currentPage': str(counter - 1),
                    'rand': '1', }).encode()
            # go to the list want to select
            selected_program_list_page = urllib.request.urlopen(for_my_program_url, selected_program_list_data)
            program_list_content = selected_program_list_page.read()
        else:
            program_list_content = first_page_content

        project_detail_link = re.findall(r'\=\"(\?action=.+?)\"\>', str(program_list_content))
        promises_list = [get_program_detail_content_promise(counter, i, project_detail_link[i]) for i in
                         range(len(project_detail_link))]

        Promise.all(promises_list).then(lambda res: resolve(res))

    return Promise(get_all_page_program_detail)


def log_in():
    # The action/ target from the form
    log_in_url = 'https://cas.uwaterloo.ca/cas/login?service=https://waterlooworks.uwaterloo.ca/waterloo.htm'

    username = input("UserName: ")
    password = input("Password: ")
    data = urllib.parse.urlencode(
        {'username': username, 'password': password, '_eventId': 'submit', 'submit': 'LOGIN',
         'lt': 'e1s1'}).encode()

    start_time = time.time()

    urllib.request.urlopen(log_in_url)
    urllib.request.urlopen(log_in_url, data)

    print("Log in Into Waterloo Website")
    # go in to the page of "For My Program"

    for_my_program_page = urllib.request.urlopen(for_my_program_url)
    for_my_program_page_content = for_my_program_page.read()

    token = ""
    token_soup = BeautifulSoup(for_my_program_page_content, "html.parser")
    for link in token_soup.findAll('a'):
        # if link.string == "For My Program ":
        if link.string == "\r\n\r\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tViewed\r\n\t\t\t\t\t\t\t\t\t\t\t\t\t":
            # if link.string == "Application Deadlines in the next 10 Days\r\n\t\t\t\t\t\t\t\t\t\t\t\t\t":
            # if link.string == "Application Deadlines Today\r\n\t\t\t\t\t\t\t\t\t\t\t\t\t":
            token = re.search("action':'(.+?)'", str(link)).group(1)

    print("Getting Program Lists")
    # try post to "For My Program"
    program_data = urllib.parse.urlencode(
        {'action': token, 'rand': '1'}).encode()
    # get the default first page
    first_page = urllib.request.urlopen(for_my_program_url, program_data)
    first_page_content = first_page.read()
    program_list_page_token = re.search(
        r"loadPostingTable\(orderBy, oldOrderBy, sortDirection, page.+?action.+?'(.+?)\\'", str(first_page_content),
        re.DOTALL).group(1)
    page_count = max(map(int, re.findall(r'null\W+?(\d+)\W+?', str(first_page_content))))


    all_pages_programs_promise_list = [
        get_all_page_program_detail_content_promise(program_list_page_token, i, first_page_content)
        for i in range(1, page_count)
    ]

    def final_call_back(data):
        print("Organizing data...")
        for words in data:
            add_word(words)
        create_dictionary()
        print("Done! ")
        print("---- %s seconds ----" % (time.time() - start_time))

    Promise.all(all_pages_programs_promise_list).then(lambda res: final_call_back(res))


log_in()
