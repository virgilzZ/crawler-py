#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import urllib.request as request
from bs4 import BeautifulSoup as bs
from retrying import retry
import threading
import time
import string
import json
import os
import re

print ('''
	=================================
	网易漫画抓取器
			--zz
	2017/6/26	16:34
	=================================
	''')

# 网易漫画分类页（抓取入口）
catalog_url = 'https://manhua.163.com/category?sort=2'
# 网易漫画详情页（章节目录页）
detail_url_163 = 'https://manhua.163.com/source/'
# 章节目录文件
catalog_json_url = 'https://manhua.163.com/book/catalog/' #4860241824180357708.json'
# 网易漫画阅读页（内容页）
comic_reader_url = 'https://manhua.163.com/reader/' # 4860241824180357708/4980407033230126791' #imgIndex=0@scale=7'

# @retry(stop_max_attempt_number=10)
@retry
def catalog_html_req(url):
	req = request.urlopen(url)
	res = req.read()
	req.close()
	return res

@retry
def comicId_json_req(csrfToken, page_size, cur_page, timestamp):
	json_url = 'https://manhua.163.com/category/getData.json?csrfToken=' + str(csrfToken) + '&sort=2&pageSize=' + str(page_size) + '&page=' + str(cur_page) + '&_=' + str(timestamp)
	req = request.urlopen(json_url)
	res = req.read()
	req.close()
	return res

@retry
def detail_html_req(comic_id):
	req = request.urlopen(detail_url_163 + str(comic_id))
	res = req.read()
	req.close()
	return res

@retry
def catalog_json_req(comic_id):
	req = request.urlopen(catalog_json_url + str(comic_id))
	res = req.read()
	req.close()
	return res

@retry
def reader_html_req(comic_id, section_id, imgIndex):
	req = request.urlopen(comic_reader_url + str(comic_id) + '/' + str(section_id) + '#imgIndex=' + str(imgIndex) + '@scale=7')
	res = req.read()
	req.close()
	return res

@retry
def img_req(img_url):
	req = request.urlopen(img_url)
	res = req.read()
	req.close()
	return res

# 获取章节列表
def get_sections(idx, comic_id, comic_list):
	print('''
		-------------------
		即将解析第 {} 部
		-------------------
		'''.format(idx))

	detail_html = detail_html_req(comic_id)
	detail_soup = bs(detail_html, 'html.parser', from_encoding='utf8')
	# 获取漫画名
	comic_name = detail_soup.title.get_text().split(',')[0]

	print('''
		--------------------------------------
		正在解析第 {} 热门漫画: {} 
		--------------------------------------
		'''.format(idx, comic_name))

	# 解析章节id
	catalog_json = catalog_json_req(comic_id)
	data = json.loads(catalog_json.decode('utf-8'))
	sections = data['catalog']['sections']
	for section_s in sections:

		thread = []
		
		for section_item in section_s['sections']:
			t = threading.Thread(target=section_img_download,
										args=(comic_id, comic_name, section_item))
			thread.append(t)
	 
		for i in range(len(section_s['sections'])):
			thread[i].start()
	 
		for i in range(len(section_s['sections'])):
			thread[i].join()
	
	# 更新序列文件
	comic_list.remove(comic_id)
	file_path = 'id_list.txt'
	sep = '\n'
	with open(file_path, 'w') as file:
		file.writelines(sep.join(comic_list))
	file.close()

	print('''
		----------------------------
		{} 下载完成	id: {}
		----------------------------
		'''.format(comic_name, comic_id))

# 解析、下载 章节图片
def section_img_download(comic_id, comic_name, section_item):
	section_id = section_item['sectionId']
	section_order = section_item['titleOrder']
	section_title = section_item['titleText']
	# 创建漫画目录
	root = 'fetch'
	comic_name = str(comic_name)
	section_name = str(section_order) + ' ' + str(section_title)
	# 过滤结尾空字符
	section_name = re.sub('\s*$', '', section_name)
	comic_dir = os.path.join(root, comic_name, section_name)
	# 文件名特殊字符过滤替换
	comic_dir = re.sub('[\/:*?"<>|]', '', comic_dir)
	print(comic_dir)
	if not os.path.isdir(comic_dir):
		os.makedirs(comic_dir)
	# 图片计数器
	imgIndex = 0
	reader_html = reader_html_req(comic_id, section_id, imgIndex)
	# 去除空格及换行
	reader_html = str(reader_html).strip().replace('\\n','')
	# print(reader_html)
	reg = r'<script>(.*?)</script>'
	script_tags = re.findall(reg, reader_html)
	for script in script_tags:
		# 解析图片路径
		reg = re.compile(r'window.PG_CONFIG.images')
		if reg.search(script):
			temp_str = script.split('window.PG_CONFIG.images = ')[1].split('[')[1].split(']')[0]
			imgs_arr = temp_str.split(',')
			for item in imgs_arr:
				# 解析图片路径
				is_exist = str(item.splitlines()).find("url: window.IS_SUPPORT_WEBP")
				# if "url: window.IS_SUPPORT_WEBP" in str(item.splitlines()):
				if is_exist > 0:
					img_url = str(item).split('" : "')[1].split('%3D')[0] + '%3D'
					img_path = os.path.join(comic_dir, str(imgIndex+1)) + '.jpg'

					if not os.path.isfile(img_path):
						img = img_req(img_url)
						with open(img_path, 'wb') as image_file:
							image_file.write(img)
							imgIndex += 1
							print(img_path)
						image_file.close()
					else:
						print(img_path + '已存在')
						imgIndex += 1
		

# 获取漫画id序列
def get_comic_id(url):
	timestamp = int(round(time.time()*1000))
	page_size = 100
	cur_page = 1
	comic_list = []
	comic_list_file = 'id_list.txt'

	if os.path.isfile(comic_list_file):
		with open(comic_list_file, 'r') as file:
			for content in file.readlines():
				comic_list.append(content.strip())
		file.close()

		print('''
			-------------------------------------
			检测到本地有 {} 条未完成序列，正在读取...
			-------------------------------------
			'''.format(len(comic_list)))

		for idx, comic_id in enumerate(comic_list, 1):
				get_sections(idx, comic_id, comic_list)
	else:

		print('''
			-------------------------------------
			正在获取第 {} ~ {} 个热门漫画序列
			-------------------------------------
			'''.format(page_size*(cur_page-1)+1, page_size*cur_page))

		catalog_html = catalog_html_req(url)
		catalog_soup = bs(catalog_html, 'html.parser', from_encoding='utf8')
		csrfToken = catalog_soup.find('input', id='j-csrf')['value']
		# 解析漫画id
		comicId_data = comicId_json_req(csrfToken, page_size, cur_page, timestamp)
		data = json.loads(comicId_data.decode('utf-8'))
		# 总分页数
		# total_page = data['pageQuery']['pageCount']
		books_arr = data['books']
		for book_item in books_arr:
			# 获取漫画信息
			comic_id = book_item['bookId']
			comic_list.append(comic_id)
			# comic_name = book_item['title']
			# update_time = book_item['latestPublishTime']

		while cur_page < 20:
			cur_page += 1

			print('''
			-------------------------------------
			正在获取第 {} ~ {} 个热门漫画序列
			-------------------------------------
			'''.format(page_size*(cur_page-1)+1, page_size*cur_page))

			# 解析漫画id
			comicId_data = comicId_json_req(csrfToken, page_size, cur_page, timestamp)
			data = json.loads(comicId_data.decode('utf-8'))
			books_arr = data['books']
			for book_item in books_arr:
				# 获取漫画信息
				comic_id = book_item['bookId']
				comic_list.append(comic_id)
				# comic_name = book_item['title']
				# update_time = book_item['latestPublishTime']

		else:
			total_num = len(comic_list)
			# 将id序列写入文件
			sep = '\n'
			with open(comic_list_file, 'w') as file:
				file.writelines(sep.join(comic_list))
			file.close()

			print('''
				----------------------------
				全部序列获取完成，共 {} 部
				----------------------------
			'''.format(total_num))

			for idx, comic_id in enumerate(comic_list, 1):
				get_sections(idx, comic_id, comic_list)



if __name__ == "__main__":
	get_comic_id(catalog_url)
