import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from grocery_flyer_watch import external_collect as c

TODAY=date(2026,11,26)
URL=c.ARCHIVE+'/canada/food-basics-flyer-november-26-to-december-22'
IMG=c.ARCHIVE+'/uploads/pages/123/food-basics-flyer-november-26-to-december-22-1.jpg'
INDEX=f'<a href="{URL}">Food Basics</a>'.encode()
PAGE=f'<p>Thu, Nov 26, 2026 - Wed, Dec 2, 2026</p><img src="{IMG}">'.encode()
LIST={'flyers':[{'id':12,'merchant':'Food Basics','valid_from':'2026-11-26','valid_to':'2026-12-02'}]}
ITEM={'id':3,'name':'Example oranges','current_price':2.99,'price_text':'2.99','description':'3 lb','valid_from':'2026-11-26','valid_to':'2026-12-02'}

def fixture(url):
    return {c.ARCHIVE+'/food-basics-canada':INDEX,URL:PAGE,IMG:b'\xff\xd8\xfffake fixture',c.FLIPP+'/flipp/flyers'+c.QUERY:json.dumps(LIST).encode(),c.FLIPP+'/flipp/flyers/12'+c.QUERY:json.dumps({'items':[ITEM]}).encode()}[url]

class CollectorTest(unittest.TestCase):
    def test_pipeline_and_idempotency(self):
        b=c.collect(TODAY,fixture)
        self.assertEqual(b['offers'][0]['price_field_cad'],'2.99')
        self.assertEqual(b['archive']['page_one_sha256'],c.digest(fixture(IMG)))
        for k in ('market_verified','coverage_complete','quality_authorized','publication_authorized','gmail_authorized'):
            self.assertIs(b[k],False)
        with tempfile.TemporaryDirectory() as d:
            p,new=c.persist(b,Path(d)); self.assertTrue(new)
            self.assertEqual(c.persist(b,Path(d)),(p,False))
            p.write_text('conflict')
            with self.assertRaises(c.CollectorError): c.persist(b,Path(d))
    def test_stale_dates(self):
        with self.assertRaises(c.CollectorError): c.collect(date(2026,12,3),fixture)
    def test_wrong_region_not_claimed(self):
        b=c.collect(TODAY,fixture); self.assertFalse(b['market_verified'])
    def test_ambiguous_flyer(self):
        def get(url):
            if url==c.FLIPP+'/flipp/flyers'+c.QUERY:
                return json.dumps({'flyers':[LIST['flyers'][0],dict(LIST['flyers'][0],id=13)]}).encode()
            return fixture(url)
        with self.assertRaisesRegex(c.CollectorError,'ambiguous'): c.collect_syndicated(TODAY,get)
    def test_no_valid_rows(self):
        for value in ('SAVE $3','2/$5',float('inf'),True):
            self.assertIsNone(c.price(value))
        with self.assertRaises(c.CollectorError): c.extract_candidates(b'{"items":[]}', '2026-11-26','2026-12-02')
    def test_invalid_item_and_private_text(self):
        raw=json.dumps({'items':[dict(ITEM,name='private@example.com'),ITEM]}).encode()
        self.assertEqual(len(c.extract_candidates(raw,'2026-11-26','2026-12-02')),1)
    def test_conflicting_rows(self):
        with self.assertRaises(c.CollectorError): c.extract_candidates(json.dumps([ITEM,dict(ITEM,current_price=3.99)]).encode(),'2026-11-26','2026-12-02')
    def test_url_allowlist(self):
        with self.assertRaises(c.CollectorError): c.fetch('https://example.invalid/')
    def test_timestamp_timezone(self):
        self.assertEqual(c.datepart('2026-12-03T04:59:59Z'),'2026-12-02')

class FallbackTests(unittest.TestCase):
    GRID=b'<h2>Top 20 Food Basics Meat, Produce &amp; Grocery Specials (Nov 26 - Dec 2)</h2><h3>Example oranges</h3><p>3 lb</p><span>$2.99 each</span><h3>Example bananas</h3><p>2/$5</p><h3>Example apples</h3><p>$1.99/lb</p><p>Avg. $2.99/lb</p><h2>Other flyers</h2><h3>Other</h3><p>$5.99 each</p>'
    def test_grid(self):
        rows=c.grid_candidates(self.GRID,'2026-11-26','2026-12-02')
        self.assertEqual([(x['name'],x['price_text']) for x in rows],[('Example oranges','$2.99 each')])
    def test_grid_stale(self):
        with self.assertRaises(c.CollectorError): c.grid_candidates(self.GRID,'2026-11-19','2026-11-25')
    def test_fixed_fallback(self):
        def get(url):
            if url==c.FLIPP+'/flipp/flyers'+c.QUERY:
                raise c.CollectorError('blocked')
            if url==c.GRID: return self.GRID
            return fixture(url)
        b=c.collect(TODAY,get)
        self.assertIn('grid',b); self.assertFalse(b['market_verified']); self.assertFalse(b['gmail_authorized'])
