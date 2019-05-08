#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# Author: _WiLloW_
# Source: https://github.com/MovistarTV/tv_grab_es_movistartv
#
# Basado en movistartv2xmltv by ese:
# https://github.com/ese/movistartv2xmltv
#
# Obtener la Lista de Canales y Programación de Movistar TV
# https://www.adslzone.net/postt359916.html
#
# ***** LICENCIA *****
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import codecs
import json
import logging
import os
import random
import re
import shutil
import socket
import struct
import sys
import time
import traceback
import urllib2
import xml.etree.cElementTree as ElTr
from HTMLParser import HTMLParser
from Queue import Queue
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from threading import Thread

demarcations = {
    'Andalucia': 15,
    'Aragon': 34,
    'Asturias': 13,
    'Cantabria': 29,
    'Catalunya': 1,
    'Castilla la Mancha': 38,
    'Castilla y Leon': 4,
    'Comunidad Valenciana': 6,
    'Extremadura': 32,
    'Galicia': 24,
    'Islas Baleares': 10,
    'Islas Canarias': 37,
    'La Rioja': 31,
    'Madrid': 19,
    'Murcia': 12,
    'Navarra': 35,
    'Pais Vasco': 36
}

default_demarcation = demarcations['Asturias']

app_dir = '/home/hts/.xmltv'
use_multithread = True
cache_exp = 3  # Días

# Generar lista de canales para udpxy
# 192.168.0.1:4022
udpxy = None

log_file = 'tv_grab_es_movistartv.log'
log_level = logging.INFO
log_size = 5  # MB

cookie_file = 'tv_grab_es_movistartv.cookie'
end_points_file = 'tv_grab_es_movistartv.endpoints'

max_credits = 4

end_points = {
    'epNoCach1': 'http://www-60.svc.imagenio.telefonica.net:2001',
    'epNoCach2': 'http://nc2.svc.imagenio.telefonica.net:2001',
    'epNoCach4': 'http://nc4.svc.imagenio.telefonica.net:2001',
    'epNoCach5': 'http://nc5.svc.imagenio.telefonica.net:2001',
    'epNoCach6': 'http://nc6.svc.imagenio.telefonica.net:2001'
}

lang = {
    'es': {'lang': 'es'},
    'en': {'lang': 'en'}
}

genre_map = {
    '0': {
        '0': 'Arts / Culture (without music)',
        '1': 'Popular culture / Traditional arts',
        '2': 'Popular culture / Traditional arts',
        '3': 'Arts magazines / Culture magazines',
        '4': 'Fine arts',
        '5': 'Fashion',
        '6': 'Broadcasting / Press',
        '7': 'Performing arts',
        '8': 'Performing arts',
        '9': 'Arts magazines / Culture magazines',
        'A': 'New media',
        'B': 'Popular culture / Traditional arts',
        'C': 'Film / Cinema',
        'D': 'Arts magazines / Culture magazines',
        'E': 'Performing arts',
        'F': 'Experimental film / Video'
    },
    '1': {
        '0': 'Movie / Drama',
        '1': 'Adventure / Western / War',
        '2': 'Romance',
        '3': 'Soap / Melodrama / Folkloric',
        '4': 'Serious / Classical / Religious / Historical movie / Drama',
        '5': 'Science fiction / Fantasy / Horror',
        '6': 'Detective / Thriller',
        '7': 'Comedy',
        '8': 'Serious / Classical / Religious / Historical movie / Drama',
        '9': 'Movie / drama',
        'A': 'Adventure / Western / War',
        'B': 'Movie / drama',
        'C': 'Adult movie / Drama',
        'D': 'Science fiction / Fantasy / Horror',
        'E': 'Adult movie / Drama',
        'F': 'Science fiction / Fantasy / Horror'
    },
    '2': {
        '0': 'Social / Political issues / Economics',
        '1': 'Magazines / Reports / Documentary',
        '2': 'Economics / Social advisory',
        '3': 'Social / Political issues / Economics',
        '4': 'Social / Political issues / Economics',
        '5': 'Social / Political issues / Economics',
        '6': 'Social / Political issues / Economics',
        '7': 'Social / Political issues / Economics',
        '8': 'Social / Political issues / Economics',
        '9': 'Social / Political issues / Economics',
        'A': 'Social / Political issues / Economics',
        'B': 'Social / Political issues / Economics',
        'C': 'Social / Political issues / Economics',
        'D': 'Social / Political issues / Economics',
        'E': 'Social / Political issues / Economics',
        'F': 'Social / Political issues / Economics',
    },
    '4': {
        '0': 'Sports',
        '1': 'Motor sport',
        '2': 'Team sports (excluding football)',
        '3': 'Water sport',
        '4': 'Team sports (excluding football)',
        '5': 'Team sports (excluding football)',
        '6': 'Martial sports',
        '7': 'Football / Soccer',
        '8': 'Water sport',
        '9': 'Team sports (excluding football)',
        'A': 'Athletics',
        'B': 'Sports',
        'C': 'Motor sport',
        'D': 'Sports',
        'E': 'Sports',
        'F': 'Tennis / Squash'
    },
    '5': {
        '0': 'Children\'s / Youth programs',
        '1': 'Entertainment programs for 10 to 16',
        '2': 'Pre-school children\'s programs',
        '3': 'Entertainment programs for 6 to 14',
        '4': 'Children\'s / Youth programs',
        '5': 'Informational / Educational / School programs',
        '6': 'Entertainment programs for 6 to 14',
        '7': 'Children\'s / Youth programs',
        '8': 'Children\'s / Youth programs',
        '9': 'Children\'s / Youth programs',
        'A': 'Children\'s / Youth programs',
        'B': 'Children\'s / Youth programs',
        'C': 'Children\'s / Youth programs',
        'D': 'Children\'s / Youth programs',
        'E': 'Children\'s / Youth programs',
        'F': 'Children\'s / Youth programs'
    },
    '6': {
        '0': 'Music / Ballet / Dance',
        '1': 'Musical / Opera',
        '2': 'Serious music / Classical music',
        '3': 'Rock / Pop',
        '4': 'Music / Ballet / Dance',
        '5': 'Music / Ballet / Dance',
        '6': 'Music / Ballet / Dance',
        '7': 'Musical / Opera',
        '8': 'Ballet',
        '9': 'Jazz',
        'A': 'Music / Ballet / Dance',
        'B': 'Rock / Pop',
        'C': 'Music / Ballet / Dance',
        'D': 'Music / Ballet / Dance',
        'E': 'Music / Ballet / Dance',
        'F': 'Music / Ballet / Dance'
    },
    '7': {
        '0': 'Show / Game show',
        '1': 'Variety show',
        '2': 'Variety show',
        '3': 'Variety show',
        '4': 'Talk show',
        '5': 'Variety show',
        '6': 'Variety show',
        '7': 'Variety show',
        '8': 'Variety show',
        '9': 'Variety show',
        'A': 'Variety show',
        'B': 'Show / Game show',
        'C': 'Talk show',
        'D': 'Show / Game show',
        'E': 'Show / Game show',
        'F': 'Show / Game show'
    },
    '8': {
        '0': 'Education / Science / Factual topics',
        '1': 'Further education',
        '2': 'Social / Spiritual sciences',
        '3': 'Medicine / Physiology / Psychology',
        '4': 'Social / Spiritual sciences',
        '5': 'Technology / Natural sciences',
        '6': 'Social / Spiritual sciences',
        '7': 'Education / Science / Factual topics',
        '8': 'Further education',
        '9': 'Nature / Animals / Environment',
        'A': 'Foreign countries / Expeditions',
        'B': 'Further education',
        'C': 'Social / Spiritual sciences',
        'D': 'Further education',
        'E': 'Education / Science / Factual topics',
        'F': 'Education / Science / Factual topics'
    },
    '9': {
        '0': 'Movie / Drama',
        '1': 'Adult movie / Drama',
        '2': 'Adult movie / Drama',
        '3': 'Adult movie / Drama',
        '4': 'Adult movie / Drama',
        '5': 'Adult movie / Drama',
        '6': 'Adult movie / Drama',
        '7': 'Adult movie / Drama',
        '8': 'Adult movie / Drama',
        '9': 'Adult movie / Drama',
        'A': 'Adult movie / Drama',
        'B': 'Adult movie / Drama',
        'C': 'Adult movie / Drama',
        'D': 'Adult movie / Drama',
        'E': 'Adult movie / Drama',
        'F': 'Adult movie / Drama'
    }
}

age_rating = ['0', '0', '0', '7', '12', '16', '17', '18']


class Error(Exception):
    pass


class MulticastError(Error):

    def __init__(self, message=''):
        if message:
            self.message = message.replace('\n', '')


class MulticastEPGFetcher(Thread):

    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            mcast = self.queue.get()
            iptv.get_day(mcast['mcast_grp'], mcast['mcast_port'], mcast['source'], mcast['day'])
            self.queue.task_done()


class Cache:

    def __init__(self):
        self.__programs = {}
        self.__end_points = None
        self.__check_dirs()
        self.__clean()

    @staticmethod
    def __check_dirs():
        cache_path = '%s/cache' % app_dir
        progs_path = '%s/programs' % cache_path
        if not os.path.isdir(cache_path):
            logger.info('Creando caché en %s' % cache_path)
            os.mkdir(cache_path)
        if not os.path.isdir(progs_path):
            os.mkdir(progs_path)

    @staticmethod
    def __clean():
        t = time.time() - (cache_exp + 2) * 86400
        for f in os.listdir('%s/cache/programs' % app_dir):
            fp = '%s/cache/programs/%s' % (app_dir, f)
            if os.path.isfile(fp) and os.stat(fp).st_mtime < t:
                os.remove(fp)
                logger.debug('Caché: %s caducado' % f)

    @staticmethod
    def __load(cfile):
        try:
            with open('%s/cache/%s' % (app_dir, cfile), 'r') as fp:
                content = json.load(fp)
            if time_start < datetime.fromtimestamp(content['expire']):
                logger.debug("Caché: %s cargado" % cfile)
                return content['data']
            else:
                logger.debug("Caché: %s caducado" % cfile)
                return None
        except IOError:
            return None

    @staticmethod
    def __save(cfile, data, expire_in=719):  # Horas
        try:
            with open('%s/cache/%s' % (app_dir, cfile), 'w') as fp:
                json.dump({'data': data, 'expire': time.time() - 900 + expire_in * 3600}, fp, indent=4)
            logger.debug("Cache: %s guardado" % cfile)
        except IOError:
            logger.error('Caché: No se puede escribir en disco')

    def load_cookie(self):
        data = self.__load(cookie_file)
        logger.info('Cookie: %s' % (data if data else 'no encontrada'))
        return data

    def save_cookie(self, data):
        logger.info('Set-Cookie: %s' % data)
        self.__save(cookie_file, data)

    def load_end_points(self):
        if not self.__end_points:
            logger.debug('End Points: buscando')
            self.__end_points = self.__load(end_points_file)
        if not self.__end_points:
            logger.debug('End Points: por defecto')
            return end_points
        return self.__end_points

    def save_end_points(self, data):
        logger.info('Nuevos End Points: %s' % data.keys())
        self.__end_points = data
        self.__save(end_points_file, data)

    def load_epg_extended_info(self, pid):
        if pid in self.__programs:
            return self.__programs[pid]
        return self.__load('programs/%s.json' % pid)

    def save_epg_extended_info(self, data):
        self.__programs[data['productID']] = data
        self.__save('programs/%s.json' % data['productID'], data, expire_in=2160)  # 3 meses

    def load_config(self):
        data = self.__load('config.json')
        if not data:
            logger.debug('Caché: configuración no encontrada')
        return data

    def save_config(self, data):
        self.__save('config.json', data, expire_in=cache_exp * 24)

    def load_service_provider_data(self):
        data = self.__load('provider.json')
        if not data:
            logger.debug('Caché: datos del Proveedor de Servicios no encontrados')
        return data

    def save_service_provider_data(self, data):
        self.__save('provider.json', data, expire_in=cache_exp * 24)

    def load_epg_data(self):
        data = self.__load('epg_metadata.json')
        if not data:
            logger.debug('Caché: metadatos de la EPG no encontrados')
        return data

    def save_epg_data(self, data):
        self.__save('epg_metadata.json', data, expire_in=cache_exp * 24)

    def load_epg(self):
        data = self.__load('epg.json')
        if not data:
            logger.debug('Caché: EPG no encontrada')
        return data

    def save_epg(self, data):
        self.__save('epg.json', data, expire_in=cache_exp * 24)


class MovistarTV:

    def __init__(self):
        self.__cookie = cache.load_cookie()
        self.__end_points_down = []
        self.__web_service_down = False

    def __get_client_profile(self):
        # noinspection PyBroadException
        try:
            logger.info('Descargando configuración del cliente')
            return json.loads(self.__get_service_data('getClientProfile'))['resultData']
        except:
            logger.error('Usando la configuración de cliente por defecto: %i|ALL|1' % default_demarcation)
            return {
                'tvPackages': 'ALL',
                'demarcation': str(default_demarcation),
                'tvWholesaler': 1
            }

    def __get_platform_profile(self):
        # noinspection PyBroadException
        try:
            logger.info('Descargando pefil del servicio')
            return json.loads(self.__get_service_data('getPlatformProfile'))['resultData']
        except:
            logger.error('Usando el pefil del servicio por defecto')
            return {
                'RES_BASE_URI': 'http://www-60.svc.imagenio.telefonica.net:2001/appclientv/nux/',
                'dvbConfig': {'dvbEntryPoint': '239.0.2.129:3937'},
                'endPoints': end_points
            }

    def __get_config_params(self):
        # noinspection PyBroadException
        try:
            logger.info('Descargando parámetros de configuración')
            return json.loads(self.__get_service_data('getConfigurationParams'))['resultData']
        except:
            logger.error('Usando los parámetros de configuración por defecto')
            return {
                'tvChannelLogoPath': 'incoming/epg/channelLogo/',
                'tvCoversPath': 'incoming/covers/programmeImages/',
                'landscapeSubPath': 'landscape/',
                'bigSubpath': 'big/'
            }

    def __get_genres(self, tv_wholesaler):
        try:
            logger.info('Descargando mapa de géneros')
            return json.loads(self.__get_service_data('getEpgSubGenres&tvWholesaler=%s' % tv_wholesaler))['resultData']
        except Exception as ex:
            logger.error('Mapa de géneros no encontrado: %s' % str(ex.args))
            return None

    def get_epg_extended_info(self, pid, channel_id):
        # noinspection PyBroadException
        try:
            data = cache.load_epg_extended_info(pid)
            if not data:
                logger.debug('Descargando info extendida: %s' % pid)
                data = json.loads(self.__get_service_data('epgInfo&extra=1&productID=%s&channelID=%s&similar=0&filterHD=1' % (pid, channel_id)))['resultData']
                cache.save_epg_extended_info(data)
            return data
        except:
            logger.error('Información extendida no encontrada: %s' % pid)
            return None

    @staticmethod
    def __get_end_points():
        try:
            return config['end_points']
        except (NameError, KeyError):
            return cache.load_end_points()

    def get_end_point(self, last_used=None):
        eps = self.__get_end_points()
        if last_used:
            self.__end_points_down.append(last_used)
            logger.error('End Point %s desactivado' % last_used)
        for ep in sorted(eps.keys()):
            if eps[ep] not in self.__end_points_down:
                return eps[ep]
        return None

    def get_first_end_point(self):
        eps = self.__get_end_points()
        for ep in sorted(eps.keys()):
            return eps[ep]

    def get_random_end_point(self):
        eps = self.__get_end_points()
        return eps[random.choice(eps.keys())]

    @staticmethod
    def __update_end_points(data):
        if cmp(cache.load_end_points(), data):
            cache.save_end_points(data)
        return data

    def get_service_config(self):
        cfg = cache.load_config()
        if cfg:
            logger.info('tvPackages: %s' % cfg['tvPackages'])
            logger.info('Demarcation: %s' % cfg['demarcation'])
            return cfg
        client = self.__get_client_profile()
        platform = self.__get_platform_profile()
        params = self.__get_config_params()
        dvb_entry_point = platform['dvbConfig']['dvbipiEntryPoint'].split(':')
        logger.info('tvPackages: %s' % client['tvPackages'])
        logger.info('Demarcation: %s' % client['demarcation'])
        conf = {
            'tvPackages': client['tvPackages'],
            'demarcation': client['demarcation'],
            'tvWholesaler': client['tvWholesaler'],
            'end_points': self.__update_end_points(platform['endPoints']),
            'mcast_grp': dvb_entry_point[0],
            'mcast_port': int(dvb_entry_point[1]),
            'tvChannelLogoPath': '%s%s' % (platform['RES_BASE_URI'], params['tvChannelLogoPath']),
            'tvCoversPath': '%s%sportrait/290x429/' % (platform['RES_BASE_URI'], params['tvCoversPath']),
            'tvCoversLandscapePath': '%s%s%s%s' % (
                platform['RES_BASE_URI'],
                params['tvCoversPath'],
                params['landscapeSubPath'],
                params['bigSubpath']),
            'genres': self.__get_genres(client['tvWholesaler'])}
        cache.save_config(conf)
        return conf

    def __get_service_data(self, action):
        if self.__web_service_down:
            return None
        ep = None
        while True:
            ep = self.get_end_point(ep)
            if not ep:
                logger.error('Servicio Web de Movistar TV caído: decargando guía básica')
                self.__web_service_down = True
                return None
            __attempts = 4
            while __attempts > 0:
                try:
                    req = urllib2.Request('%s/appserver/mvtv.do?action=%s' % (ep, action))
                    if self.__cookie:
                        for ck in self.__cookie.split('; '):
                            if '=' in ck:
                                req.add_header('Cookie', self.__cookie)
                    response = urllib2.urlopen(req, timeout=15)
                    content = response.read().decode(response.headers.getparam('charset') or 'utf-8')
                    response.close()
                    if response.getcode() == 200:
                        new_cookie = response.headers.dict['set-cookie'] \
                            if 'set-cookie' in response.headers.dict else None
                        if new_cookie and not self.__cookie:
                            self.__cookie = new_cookie
                            cache.save_cookie(self.__cookie)
                        elif new_cookie and new_cookie != self.__cookie:
                            cache.save_cookie(new_cookie)
                        return content
                    raise urllib2.HTTPError
                except (urllib2.HTTPError, socket.timeout, urllib2.URLError):
                    __attempts -= 1
                    logger.warn('Timeout: %s, reintentos: %s' % (ep, __attempts))
                    continue


class MulticastIPTV:

    def __init__(self):
        self.__xml_data = {}
        self.__epg = None

    @staticmethod
    def __parse_chunk(data):
        try:
            chunk = {
                "end": struct.unpack('B', data[:1])[0],
                "size": struct.unpack('>HB', data[1:4])[0],
                "filetype": struct.unpack('B', data[4:5])[0],
                "fileid": struct.unpack('>H', data[5:7])[0] & 0x0fff,
                "chunk_number": struct.unpack('>H', data[8:10])[0] / 0x10,
                "chunk_total": struct.unpack('B', data[10:11])[0],
                "data": data[12:]
            }
            return chunk
        except Exception as ex:
            raise MulticastError('get_chunk: error al analizar los datos %s' % str(ex.args))

    def __get_xml_files(self, mc_grp, mc_port):
        try:
            loop = True
            chunk = {"end": 0}
            max_files = 1000
            _files = {}
            first_file = ''
            logger.debug('Descargando XML de %s:%s' % (mc_grp, mc_port))
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(3)
            sock.bind((mc_grp, int(mc_port)))
            mreq = struct.pack("=4sl", socket.inet_aton(mc_grp), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            # Wait for an end chunk to start by the beginning
            while not (chunk["end"]):
                chunk = self.__parse_chunk(sock.recv(1500))
                first_file = str(chunk["filetype"]) + "_" + str(chunk["fileid"])
            # Loop until firstfile
            while loop:
                xmldata = ""
                chunk = self.__parse_chunk(sock.recv(1500))
                # Discard headers
                body = chunk["data"]
                while not (chunk["end"]):
                    xmldata += body
                    chunk = self.__parse_chunk(sock.recv(1500))
                    body = chunk["data"]
                # Discard last 4bytes binary footer?
                xmldata += body[:-4]
                _files[str(chunk["filetype"]) + "_" + str(chunk["fileid"])] = xmldata
                logger.debug('XML: %s_%s' % (chunk["filetype"], chunk["fileid"]))
                max_files -= 1
                if str(chunk["filetype"]) + "_" + str(chunk["fileid"]) == first_file or max_files == 0:
                    loop = False
            sock.close()
            return _files
        except Exception, ex:
            logger.error('Error al descargar los archivos XML: %s' % str(ex.args))

    @staticmethod
    def __get_channels(xml_channels):
        root = ElTr.fromstring(xml_channels.replace('\n', ' '))
        services = root[0][0].findall("{urn:dvb:ipisdns:2006}SingleService")
        channel_list = {}
        for i in services:
            channel_id = 'unknown'
            try:
                channel_id = i[1].attrib['ServiceName']
                channel_list[channel_id] = {
                    'id': channel_id,
                    'address': i[0][0].attrib['Address'],
                    'port': i[0][0].attrib['Port'],
                    'name': i[2][0].text,
                    'shortname': i[2][1].text,
                    'genre': i[2][3][0].text,
                    'logo_uri': i[1].attrib['logoURI'] if 'logoURI' in i[1].attrib else 'MAY_1/imSer/4146.jpg'}
                if i[2][4].tag == '{urn:dvb:ipisdns:2006}ReplacementService':
                    channel_list[channel_id]['replacement'] = i[2][4][0].attrib['ServiceName']
            except (KeyError, IndexError) as ex:
                logger.debug('El canal %s no tiene la estructura correcta: %s' % (channel_id, str(ex.args)))
        logger.info('Canales: %i' % len(channel_list))
        return channel_list

    @staticmethod
    def __get_packages(xml):
        root = ElTr.fromstring(xml.replace('\n', ' '))
        packages = root[0].findall("{urn:dvb:ipisdns:2006}Package")
        package_list = {}
        for package in packages:
            package_name = 'unknown'
            try:
                package_name = package[0].text
                package_list[package_name] = {
                    'id': package.attrib['Id'],
                    'name': package_name,
                    'services': {}}
                for service in package:
                    if not service.tag == '{urn:dvb:ipisdns:2006}PackageName':
                        service_id = service[0].attrib['ServiceName']
                        package_list[package_name]['services'][service_id] = service[1].text
            except (KeyError, ElTr.ParseError) as ex:
                logger.error('El paquete %s no tiene la estructura correcta: %s' % (package_name, str(ex.args)))
        logger.info('Paquetes: %i' % len(package_list))
        return package_list

    @staticmethod
    def __get_segments(xml):
        root = ElTr.fromstring(xml.replace('\n', ' '))
        payloads = root[0][1][1].findall("{urn:dvb:ipisdns:2006}DVBBINSTP")
        segment_list = {}
        for segments in payloads:
            source = 'unknown'
            try:
                source = segments.attrib['Source']
                segment_list[source] = {
                    'Source': source,
                    'Port': segments.attrib['Port'],
                    'Address': segments.attrib['Address'],
                    'Segments': {}}
                for segment in segments[0]:
                    segment_id = segment.attrib['ID']
                    segment_list[source]['Segments'][segment_id] = segment.attrib['Version']
            except KeyError:
                logger.error('El segment %s no tiene la estructura correcta' % source)
        logger.info('Días de EPG: %i' % len(segment_list))
        return segment_list

    @staticmethod
    def __get_demarcation_name():
        for demarcation in demarcations:
            if demarcations[demarcation] == config['demarcation']:
                return demarcation
        return config['demarcation']

    def __get_service_provider_ip(self):
        # noinspection PyBroadException
        try:
            logger.info('Buscando el Proveedor de Servicios de %s' % self.__get_demarcation_name())
            data = cache.load_service_provider_data()
            if not data:
                xml = self.__get_xml_files(config['mcast_grp'], config['mcast_port'])['1_0']
                result = re.findall(
                    'DEM_' + str(config['demarcation']) +
                    '\..*?Address=\"(.*?)\".*?\s*Port=\"(.*?)\".*?', xml, re.DOTALL)[0]
                data = {
                    'mcast_grp': result[0],
                    'mcast_port': result[1]
                }
                cache.save_service_provider_data(data)
            logger.info('Proveedor de Servicios de %s: %s' % (self.__get_demarcation_name(), data['mcast_grp']))
            return data
        except:
            logger.error('Usando el Proveedor de Servicios por defecto: 239.0.2.150')
            return {
                'mcast_grp': '239.0.2.150',
                'mcast_port': '3937'
            }

    def __get_bin_epg(self):
        self.__epg = []
        for key in sorted(self.__xml_data['segments'].keys()):
            logger.info('Descargando %s' % key)
            self.__epg.append(self.__get_xml_files(
                self.__xml_data['segments'][key]['Address'],
                self.__xml_data['segments'][key]['Port'])
            )

    def get_day(self, mcast_grp, mcast_port, source, day):
        logger.info('Descargando %s' % source)
        self.__epg[day] = self.__get_xml_files(mcast_grp, mcast_port)

    def __get_bin_epg_threaded(self):
        queue = Queue()
        threads = 3
        day = -1
        # noinspection PyUnusedLocal
        self.__epg = [{} for r in range(0, len(self.__xml_data['segments']))]
        logger.info('Multithread: %s descargas simultáneas' % threads)
        for n in range(threads):
            process = MulticastEPGFetcher(queue)
            process.setDaemon(True)
            process.start()
        for key in sorted(self.__xml_data['segments'].keys()):
            day += 1
            queue.put({
                'mcast_grp': self.__xml_data['segments'][key]['Address'],
                'mcast_port': self.__xml_data['segments'][key]['Port'],
                'source': key,
                'day': day,
            })
        queue.join()

    def get_epg(self):
        data = cache.load_epg()
        if data:
            logger.debug('Canales con EPG: %s' % len(data))
            return data
        if use_multithread:
            self.__get_bin_epg_threaded()
        else:
            self.__get_bin_epg()
        return self.__parse_bin_epg()

    def __get_epg_data(self, mcast_grp, mcast_port):
        data = cache.load_epg_data()
        if data:
            logger.info('Canales: %i' % len(data['channels']))
            logger.info('Paquetes: %i' % len(data['packages']))
            logger.info('Días de EPG: %i' % len(data['segments']))
            self.__xml_data = data
        else:
            logger.info('Descargando canales, paquetes e índices')
            xml = self.__get_xml_files(mcast_grp, mcast_port)
            self.__xml_data = {
                'channels': self.__get_channels(xml['2_0']),
                'packages': self.__get_packages(xml['5_0']),
                'segments': self.__get_segments(xml['6_0'])}
            cache.save_epg_data(self.__xml_data)

    def get_service_provider_data(self):
        if not self.__xml_data:
            connection = self.__get_service_provider_ip()
            self.__get_epg_data(connection['mcast_grp'], connection['mcast_port'])
        return self.__xml_data

    @staticmethod
    def __decode_string(string):
        return ''.join(chr(ord(char) ^ 0x15) for char in string)

    @staticmethod
    def __parse_bin_epg_header(data):
        # noinspection PyBroadException
        try:
            body = struct.unpack('B', data[6:7])[0] + 7
            return {
                'size': struct.unpack('>H', data[1:3])[0],
                'service_id': struct.unpack('>H', data[3:5])[0],
                'service_version': struct.unpack('B', data[5:6])[0],
                'service_url': data[7:body],
                'data': data[body:]
            }
        except Exception as ex:
            logger.error('Error al procesar la cabecera: %s' % str(ex.args))

    @staticmethod
    def __sanitize(text):
        try:
            return HTMLParser().unescape(unicode(text, 'utf-8'))
        except TypeError:
            return text

    def __parse_bin_epg_body(self, data):
        epg_dt = data[:-4]
        # noinspection PyBroadException
        try:
            programs = {}
            while epg_dt:
                start = struct.unpack('>I', epg_dt[4:8])[0]
                duration = struct.unpack('>H', epg_dt[8:10])[0]
                title_end = struct.unpack('B', epg_dt[31:32])[0] + 32
                pr_title_end = None
                programs[start] = {
                    'pid': struct.unpack('>I', epg_dt[:4])[0],
                    'start': start,
                    'duration': duration,
                    'end': start + duration,
                    'genre': '{:02X}'.format(struct.unpack('B', epg_dt[20:21])[0]),
                    'age_rating': struct.unpack('B', epg_dt[24:25])[0],
                    'full_title': self.__sanitize(self.__decode_string(epg_dt[32:title_end])),
                    'is_serie': True if struct.unpack('B', epg_dt[title_end:title_end + 1])[0] == 0xF1 else False
                }
                if programs[start]['is_serie']:
                    pr_title = programs[start]['full_title'].split(' - ')
                    pr_title_end = struct.unpack('B', epg_dt[title_end + 12:title_end + 13])[0] + title_end + 13
                    if len(pr_title) == 2:
                        programs[start]['episode_title'] = self.__sanitize(pr_title[1])
                    programs[start].update({
                        'serie_id': struct.unpack('>H', epg_dt[title_end + 5:title_end + 7])[0],
                        'episode': struct.unpack('B', epg_dt[title_end + 8:title_end + 9])[0],
                        'year': str(struct.unpack('>H', epg_dt[title_end + 9:title_end + 11])[0]),
                        'season': struct.unpack('B', epg_dt[title_end + 11:title_end + 12])[0],
                        'serie': self.__sanitize(self.__decode_string(epg_dt[title_end + 13:pr_title_end]))
                    })
                cut = pr_title_end if pr_title_end else title_end
                epg_dt = epg_dt[struct.unpack('B', epg_dt[cut + 3:cut + 4])[0] + cut + 4:]
            return programs
        except Exception as ex:
            logger.error('Error al procesar la guía: %s' % str(ex.args))

    def __merge_dicts(self, dict1, dict2, path=None):
        path = [] if path is None else path
        for key in dict2:
            if key in dict1:
                if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                    self.__merge_dicts(dict1[key], dict2[key], path + [str(key)])
                elif dict1[key] == dict2[key]:
                    pass
                else:
                    raise Exception('Conflicto en %s' % '.'.join(path + [str(key)]))
            else:
                dict1[key] = dict2[key]
        return dict1

    def __parse_bin_epg(self):
        merged_epg = {}
        for epg_day in self.__epg:
            programs = {}
            for ch_id in epg_day.keys():
                if epg_day[ch_id] and 'replacement' not in epg_day[ch_id]:
                    head = self.__parse_bin_epg_header(epg_day[ch_id])
                    programs[str(head['service_id'])] = self.__parse_bin_epg_body(head['data'])
            self.__merge_dicts(merged_epg, programs)
        logger.debug('Canales con EPG: %s' % len(merged_epg))
        cache.save_epg(merged_epg)
        return merged_epg


class XMLTV:

    def __init__(self, data):
        self.__channels = data['channels']
        self.__packages = data['packages']

    def generate_xml(self, parsed_epg):
        logger.info('Generando la guía XMLTV: descargando info extendida')
        root = ElTr.Element('tv', {
                'date': datetime.now().strftime('%Y%m%d%H%M%S'),
                'source_info_url': 'https://github.com/MovistarTV/tv_grab_es_movistartv',
                'source_info_name': 'Grabber for Movistar TV Multicast EPG',
                'generator_info_name': 'tv_grab_es_movistartv',
                'generator_info_url': 'http://wiki.xmltv.org/index.php/XMLTVFormat'})
        tz = abs(time.timezone / 3600) + time.localtime().tm_isdst
        services = self.__get_client_channels()
        for channel_id in sorted(services, key=lambda key: int(services[key])):
            if channel_id in self.__channels:
                tag_channel = ElTr.Element('channel', {'id': '%s.movistar.tv' % channel_id})
                tag_dname = ElTr.SubElement(tag_channel, 'display-name')
                tag_dname.text = self.__channels[channel_id]['name']
                root.append(tag_channel)
            else:
                logger.debug('El canal %s no tiene EPG' % channel_id)
        for channel_id in sorted(services, key=lambda key: int(services[key])):
            if channel_id in self.__channels:
                chid = self.__channels[channel_id]['replacement'] \
                    if 'replacement' in self.__channels[channel_id] else channel_id
                if chid in parsed_epg:
                    for program in sorted(parsed_epg[chid].keys()):
                        if parsed_epg[chid][program]['end'] > time.time() - 7200:
                            root.append(self.__build_programme_tag(channel_id, parsed_epg[chid][program], tz))
        return ElTr.ElementTree(root)

    @staticmethod
    def __get_genre_and_subgenre(code):
        return {
            'genre': genre_map[code[0]]['0'],
            'sub-genre': None if code[1] == '0' else genre_map[code[0]][code[1]]
        }

    @staticmethod
    def __get_key_and_subkey(code, genres):
        if not genres:
            return None
        genre = next(genre for genre in genres if genre['id'].upper() == (code[0] if code[0] == '0' else ('%s%s' % (code[0], '0')).upper()))
        subgenre = None if code[1] == '0' else next(subgenre for subgenre in genre['subgenres'] if subgenre['id'].upper() == (code[1].upper() if code[0] == '0' else ('%s%s' % (code[0], code[1])).upper()))
        return {
            'key': genre['name'],
            'sub-key': subgenre['name'] if subgenre else None
        }

    @staticmethod
    def __get_series_data(program, ext_info):
        episode = int(program['episode'])
        season = int(program['season'])
        desc = ext_info['synopsis'] if ext_info else u'Año: %s' % program['year']
        if season == 0:
            sn = re.findall(r'.*\sT(\d*/?\d+).*', program['full_title'], re.U)
            season = int(sn[0].replace('/', '')) if sn else season
        if 'episode_title' in program:
            title = program['serie']
            stitle = '%ix%02d %s' % (season, episode, program['episode_title'])
        else:
            title = re.findall(r'(.*)\sT\d*/?\d+.*', program['full_title'], re.U)
            title = title[0] if title else program['full_title']
            stitle = '%ix%02d %s' % (
                season, episode, ext_info['originalTitle']
                if ext_info and 'originalTitle' in ext_info else 'Episodio %i' % episode
            )
        return {
            'title': title,
            'sub-title': stitle,
            'season': season if season > 0 else '',
            'episode': episode,
            'desc': desc
        }

    def __build_programme_tag(self, channel_id, program, tz):
        start = datetime.fromtimestamp(program['start']).strftime('%Y%m%d%H%M%S')
        stop = datetime.fromtimestamp(program['end']).strftime('%Y%m%d%H%M%S')
        tag_programme = ElTr.Element('programme', {
            'channel': '%s.movistar.tv' % channel_id,
            'start': '%s +0%s00' % (start, tz),
            'stop': '%s +0%s00' % (stop, tz)})
        tag_title = ElTr.SubElement(tag_programme, 'title', lang['es'])
        tag_title.text = program['full_title']
        gens = self.__get_genre_and_subgenre(program['genre'])
        keys = self.__get_key_and_subkey(program['genre'], config['genres'])
        ext_info = mtv.get_epg_extended_info(program['pid'], channel_id)
        # Series
        if program['serie_id'] > 0:
            tsse = self.__get_series_data(program, ext_info)
            tag_title.text = tsse['title']
            tag_stitle = ElTr.SubElement(tag_programme, 'sub-title', lang['es'])
            tag_stitle.text = tsse['sub-title']
            tag_desc = ElTr.SubElement(tag_programme, 'desc', lang['es'])
            tag_desc.text = tsse['desc']
            tag_date = ElTr.SubElement(tag_programme, 'date')
            tag_date.text = program['year']
            tag_episode_num = ElTr.SubElement(tag_programme, 'episode-num', {'system': 'xmltv_ns'})
            tag_episode_num.text = '%s.%i.' % (
                '%i' % (tsse['season'] - 1) if tsse['season'] else '', tsse['episode'] - 1)
        # Películas y otros
        elif ext_info:
            if 'Movie' in gens['genre'] and 'productionDate' in ext_info:
                tag_stitle = ElTr.SubElement(tag_programme, 'sub-title', lang['es'])
                tag_stitle.text = str(ext_info['productionDate'])
            tag_desc = ElTr.SubElement(tag_programme, 'desc', lang['es'])
            tag_desc.text = ext_info['synopsis']
            if 'productionDate' in ext_info:
                tag_date = ElTr.SubElement(tag_programme, 'date')
                tag_date.text = str(ext_info['productionDate'])
        # Comunes a los tres
        if ext_info:
            if ('mainActors' or 'directors') in ext_info:
                tag_credits = ElTr.SubElement(tag_programme, 'credits')
                if 'directors' in ext_info:
                    length = len(ext_info['directors']) if len(ext_info['directors']) <= max_credits else max_credits
                    for director in ext_info['directors'][:length]:
                        tag_director = ElTr.SubElement(tag_credits, 'director')
                        tag_director.text = director.strip()
                if 'mainActors' in ext_info:
                    length = len(ext_info['mainActors']) if len(ext_info['mainActors']) <= max_credits else max_credits
                    for actor in ext_info['mainActors'][:length]:
                        tag_actor = ElTr.SubElement(tag_credits, 'actor')
                        tag_actor.text = actor.strip()
            ElTr.SubElement(tag_programme, 'icon', {
                    'src': '%s%s' % (config['tvCoversPath'], ext_info['cover'])})
        tag_original_title = ElTr.SubElement(tag_programme, 'original-title')
        tag_original_title.text = '%s|%s' % (channel_id, program['pid'])
        tag_rating = ElTr.SubElement(tag_programme, 'rating', {'system': 'pl'})
        tag_value = ElTr.SubElement(tag_rating, 'value')
        tag_value.text = age_rating[program['age_rating']]
        tag_category = ElTr.SubElement(tag_programme, 'category', lang['en'])
        tag_category.text = gens['genre']
        if gens['sub-genre']:
            tag_subcategory = ElTr.SubElement(tag_programme, 'category', {'lang': 'en'})
            tag_subcategory.text = gens['sub-genre']
        if keys:
            tag_keyword = ElTr.SubElement(tag_programme, 'keyword')
            tag_keyword.text = keys['key']
            if keys['sub-key']:
                tag_subkeyword = ElTr.SubElement(tag_programme, 'keyword')
                tag_subkeyword.text = keys['sub-key']
        return tag_programme

    def write_m3u(self, file_path):
        m3u = self.__generate_m3u()
        self.__write_to_disk(file_path, m3u)

    def __get_client_channels(self):
        services = {}
        for package in config['tvPackages'].split('|') if config['tvPackages'] != 'ALL' else self.__packages.keys():
            if package in self.__packages:
                services.update(self.__packages[package]['services'])
        return services

    def __generate_m3u(self):
        m3u = '#EXTM3U\n'
        services = self.__get_client_channels()
        for channel_id in sorted(services, key=lambda key: int(services[key])):
            if channel_id in self.__channels:
                channel_name = self.__channels[channel_id]['name']
                channel_key = channel_id
                channel_ip = self.__channels[channel_id]['address']
                channel_port = str(self.__channels[channel_id]['port'])
                channel_tag = self.__channels[channel_id]['genre']
                channel_number = services[channel_id]
                channel_quality = 'HDTV' if 'HD' in channel_name else 'SDTV'
                channel_logo = '%s%s' % (config['tvChannelLogoPath'], self.__channels[channel_id]['logo_uri'])
                if 'replacement' in self.__channels[channel_id]:
                    channel_key = self.__channels[self.__channels[channel_id]['replacement']]['id']
                m3u += '#EXTINF:-1 tvh-epg="disable" tvh-chnum="%s" ' % channel_number
                m3u += 'tvg-id="%s.movistar.tv" tvh-tags="Movistar TV|%s|%s" ' % (
                    channel_key, channel_quality, channel_tag)
                m3u += 'tvg-logo="%s",%s\n' % (channel_logo, channel_name)
                if udpxy:
                    m3u += 'http://%s/udp/%s:%s\n' % (udpxy, channel_ip, channel_port)
                else: m3u += 'rtp://@%s:%s\n' % (channel_ip, channel_port)
        return m3u

    @staticmethod
    def __write_to_disk(file_path, content):
        try:
            with codecs.open(file_path, 'w', 'UTF-8') as file_h:
                file_h.write(content)
                file_h.close()
        except IOError:
            logger.error('No se puede escribir en disco')


def create_logger(argv):
    if not os.path.isdir(app_dir):
        os.mkdir(app_dir)
    log_path = '%s/%s' % (app_dir, log_file)
    handler = RotatingFileHandler(log_path, mode='a', maxBytes=log_size*1048576, backupCount=2, encoding=None, delay=0)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', '%d/%m/%Y %H:%M:%S')
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    logger_h = logging.getLogger('movistartv.epg.xmltv')
    logger_h.setLevel(log_level)
    logger_h.addHandler(handler)
    logger_h.info('---------------------------------------------------')
    logger_h.info('MovistarTV EPG Grabber')
    logger_h.info('Parámetros: %s' % argv[1:])
    logger_h.info('---------------------------------------------------')
    return logger_h


def create_args_parser():
    now = datetime.now()
    desc = 'Grab Movistar TV EPG guide via Multicast from %s to %s' % (
        (now - timedelta(hours=2)).strftime('%d/%m/%Y'),
        (now + timedelta(days=4)).strftime('%d/%m/%Y'))
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--description',
                        help="Show 'Spain (MovistarTV)'",
                        action='store_true')
    parser.add_argument('--capabilities',
                        help='Show xmltv capabilities',
                        action='store_true')
    parser.add_argument('--output',
                        help='Redirect the xmltv output to the specified file. Otherwise output goes to stdout.',
                        action='store',
                        dest='filename',
                        default='')
    parser.add_argument('--m3u',
                        help='Dump channels in m3u format to the specified file.',
                        action='store',
                        dest='output',
                        default='')
    parser.add_argument('--tvheadend',
                        help="Grab EPG and dump channels in m3u format to CHANNELS file (use this argument in "
                             "TVHeadend grabber's configuration page to update both: the EPG guide and the "
                             "m3u channel list)",
                        action='store',
                        dest='channels',
                        default='')
    parser.add_argument('--reset',
                        help='Delete saved configuration, log file and caches.',
                        action='store_true')
    return parser


def show_description():
    logger.info('Terminado: descripción del grabber')
    print 'Spain (MovistarTV)'
    sys.exit(0)


def show_capabilities():
    logger.info('Terminado: capabilities del grabber')
    print 'baseline cache'
    sys.exit(0)


def reset():
    logger.info('Terminado: eliminado el log, la configuración y la caché')
    shutil.rmtree(app_dir, ignore_errors=True)
    sys.exit(0)


def export_channels(m3u_file):
    xmltv.write_m3u(m3u_file)
    logger.info('Lista de canales exportada: %s' % m3u_file)


# Guarda el timestamp de inicio
time_start = datetime.now()

# Crea el logger
logger = create_logger(sys.argv)

try:
    # Obtiene los argumentos de entrada
    args = create_args_parser().parse_args()

    if args.description:
        show_description()

    if args.capabilities:
        show_capabilities()

    if args.reset:
        reset()

    # Crea la caché
    cache = Cache()

    # Descarga la configuración del servicio Web de MovistarTV
    mtv = MovistarTV()
    config = mtv.get_service_config()

    # Busca el Proveedor de Servicios y descarga los archivos XML: canales, paquetes y segments
    iptv = MulticastIPTV()
    xdata = iptv.get_service_provider_data()

    # Crea el objeto XMLTV a partir de los datos descargados del Proveedor de Servicios
    xmltv = XMLTV(xdata)

    if args.output:
        export_channels(args.output)
        sys.exit(0)

    # Descarga los segments de cada EPG_X_BIN.imagenio.es y devuelve la guía decodificada
    epg = iptv.get_epg()

    # Genera el árbol XMLTV de los paquetes contratados
    epg_x = xmltv.generate_xml(epg)

    if args.filename:
        logger.info('Guardando la guía XMLTV: %s' % args.filename)
        epg_x.write(args.filename, encoding="UTF-8")
    else:
        if args.channels:
            export_channels(args.channels)
        print ElTr.tostring(epg_x.getroot(), encoding='UTF-8', method="xml")

    # Muestra la duración del script y el número de canales y días de EPG descargados
    total = (int(datetime.now().strftime('%s')) - int(time_start.strftime('%s'))) / 60
    logger.info('EPG de %i canales y %i días %s' % (
        len(epg),
        len(xdata['segments']),
        'descargada en %i minutos' % total if total != 0 else
        'generada en %i segundos' % (int(datetime.now().strftime('%s')) - int(time_start.strftime('%s')))))

    sys.exit(0)

except Exception as e:
    logger.critical('%s\n%s' % (e.message, traceback.format_exc()))
    print u'Excepción:\n\n\t %s\n\nTraceback:\n\n\t%s' % (e.message, traceback.format_exc())
    sys.exit(1)
