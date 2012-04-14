from django import template
from django.test import TestCase
from django.core.cache import cache
from django.contrib.auth.models import User
from django import db

from flatblocks.models import FlatBlock
from flatblocks.templatetags.flatblock_tags import do_get_flatblock
from flatblocks import settings


class BasicTests(TestCase):
    urls = 'flatblocks.urls'

    def setUp(self):
        self.testblock = FlatBlock.objects.create(
             slug='block',
             header='HEADER',
             content='CONTENT'
        )
        self.admin = User.objects.create_superuser('admin', 'admin@localhost', 'adminpwd')

    def testURLConf(self):
        # We have to support two different APIs here (1.1 and 1.2)
        def get_tmpl(resp):
            if isinstance(resp.template, list):
                return resp.template[0]
            return resp.template
        self.assertEquals(get_tmpl(self.client.get('/edit/1/')).name, 'admin/login.html')
        self.client.login(username='admin', password='adminpwd')
        self.assertEquals(get_tmpl(self.client.get('/edit/1/')).name, 'flatblocks/edit.html')

    def testCacheReset(self):
        """
        Tests if FlatBlock.save() resets the cache.
        """
        tpl = template.Template('{% load flatblock_tags %}{% flatblock "block" 60 %}')
        tpl.render(template.Context({}))
        name = '%sblock' % settings.CACHE_PREFIX
        self.assertNotEquals(None, cache.get(name))
        block = FlatBlock.objects.get(slug='block')
        block.header = 'UPDATED'
        block.save()
        self.assertEquals(None, cache.get(name))

    def testSaveKwargs(self):
        block = FlatBlock(slug='missing')
#        block.slug = 'missing'
        self.assertRaises(ValueError, block.save, force_update=True)
        block = FlatBlock.objects.get(slug='block')
        self.assertRaises(db.IntegrityError, block.save, force_insert=True)

    def testCacheRemoval(self):
        """
        If a block is deleted it should also be removed from the cache.
        """
        block = FlatBlock(slug="test", content="CONTENT")
        block.save()
        tpl = template.Template('{% load flatblock_tags %}{% flatblock "test" 100 %}')
        # We fill the cache by rendering the block
        tpl.render(template.Context({}))
        cache_key = "%stest" % settings.CACHE_PREFIX
        self.assertNotEquals(None, cache.get(cache_key))
        block.delete()
        self.assertEquals(None, cache.get(cache_key))


class TagTests(TestCase):
    def setUp(self):
        self.testblock = FlatBlock.objects.create(
             slug='block',
             header='HEADER',
             content='CONTENT'
        )

    def testLoadingTaglib(self):
        """Tests if the taglib defined in this app can be loaded"""
        tpl = template.Template('{% load flatblock_tags %}')
        tpl.render(template.Context({}))

    def testExistingPlain(self):
        tpl = template.Template('{% load flatblock_tags %}{% plain_flatblock "block" %}')
        self.assertEqual(u'CONTENT', tpl.render(template.Context({})).strip())

    def testExistingTemplate(self):
        expected = """<div class="flatblock block-block">

    <h2 class="title">HEADER</h2>

    <div class="content">CONTENT</div>
</div>
"""
        tpl = template.Template('{% load flatblock_tags %}{% flatblock "block" %}')
        self.assertEqual(expected, tpl.render(template.Context({})))

    def testUsingMissingTemplate(self):
        tpl = template.Template('{% load flatblock_tags %}{% flatblock "block" using "missing_template.html" %}')
        exception = template.TemplateSyntaxError
        self.assertRaises(exception, tpl.render, template.Context({}))

    def testSyntax(self):
        tpl = template.Template('{% load flatblock_tags %}{% flatblock "block" %}')
        tpl.render(template.Context({}))
        node = do_get_flatblock(None, template.Token('TOKEN_TEXT', 'flatblock "block"'))
        self.assertEquals('block', node.slug)
        self.assertEquals(False, node.evaluated)

        tpl = template.Template('{% load flatblock_tags %}{% flatblock "block" 123 %}')
        tpl.render(template.Context({}))
        node = do_get_flatblock(None, template.Token('TOKEN_TEXT', 'flatblock "block" 123'))
        self.assertEquals('block', node.slug)
        self.assertEquals(False, node.evaluated)
        self.assertEquals(123, node.cache_time)

        tpl = template.Template('{% load flatblock_tags %}{% flatblock "block" using "flatblocks/flatblock.html" %}')
        tpl.render(template.Context({}))
        node = do_get_flatblock(None, template.Token('TOKEN_TEXT', 'flatblock "block" using "flatblocks/flatblock.html"'))
        self.assertEquals('block', node.slug)
        self.assertEquals(False, node.evaluated)
        self.assertEquals(0, node.cache_time)
        self.assertEquals("flatblocks/flatblock.html", node.template_name)

        tpl = template.Template('{% load flatblock_tags %}{% flatblock "block" 123 using "flatblocks/flatblock.html" %}')
        tpl.render(template.Context({}))
        node = do_get_flatblock(None, template.Token('TOKEN_TEXT', 'flatblock "block" 123 using "flatblocks/flatblock.html"'))
        self.assertEquals('block', node.slug)
        self.assertEquals(False, node.evaluated)
        self.assertEquals(123, node.cache_time)
        self.assertEquals("flatblocks/flatblock.html", node.template_name)

        tpl = template.Template('{% load flatblock_tags %}{% flatblock "block" evaluated %}')
        tpl.render(template.Context({}))
        node = do_get_flatblock(None, template.Token('TOKEN_TEXT', 'flatblock "block" evaluated'))
        self.assertEquals('block', node.slug)
        self.assertEquals(True, node.evaluated)
        self.assertEquals(0, node.cache_time)

        tpl = template.Template('{% load flatblock_tags %}{% flatblock "block" evaluated using "flatblocks/flatblock.html" %}')
        tpl.render(template.Context({}))
        node = do_get_flatblock(None, template.Token('TOKEN_TEXT', 'flatblock "block" evaluated using "flatblocks/flatblock.html"'))
        self.assertEquals('block', node.slug)
        self.assertEquals(True, node.evaluated)
        self.assertEquals(0, node.cache_time)
        self.assertEquals("flatblocks/flatblock.html", node.template_name)

        tpl = template.Template('{% load flatblock_tags %}{% flatblock "block" 123 evaluated %}')
        tpl.render(template.Context({}))
        node = do_get_flatblock(None, template.Token('TOKEN_TEXT', 'flatblock "block" 123 evaluated'))
        self.assertEquals(123, node.cache_time)
        self.assertEquals(True, node.evaluated)

        tpl = template.Template('{% load flatblock_tags %}{% flatblock "block" 123 evaluated using "flatblocks/flatblock.html" %}')
        tpl.render(template.Context({}))
        node = do_get_flatblock(None, template.Token('TOKEN_TEXT', 'flatblock "block" 123 evaluated using "flatblocks/flatblock.html"'))
        self.assertEquals('block', node.slug)
        self.assertEquals(True, node.evaluated)
        self.assertEquals(123, node.cache_time)
        self.assertEquals("flatblocks/flatblock.html", node.template_name)


    def testBlockAsVariable(self):
        tpl = template.Template('{% load flatblock_tags %}{% flatblock blockvar %}')
        tpl.render(template.Context({'blockvar': 'block'}))

    def testContentEvaluation(self):
        """
        If a block is set in the template to be evaluated the actual content of the block is treated
        as a Django template and receives the parent template's context.
        """
        FlatBlock.objects.create(
             slug='tmpl_block',
             header='HEADER',
             content='{{ variable }}'
        )
        tpl = template.Template('{% load flatblock_tags %}{% plain_flatblock "tmpl_block" evaluated %}')
        result = tpl.render(template.Context({'variable': 'value'}))
        self.assertEquals('value', result)

    def testDisabledEvaluation(self):
        """
        If "evaluated" is not passed, no evaluation should take place.
        """
        FlatBlock.objects.create(
             slug='tmpl_block',
             header='HEADER',
             content='{{ variable }}'
        )
        tpl = template.Template('{% load flatblock_tags %}{% plain_flatblock "tmpl_block" %}')
        result = tpl.render(template.Context({'variable': 'value'}))
        self.assertEquals('{{ variable }}', result)

    def testHeaderEvaluation(self):
        """
        Also the header should receive the context and get evaluated.
        """
        FlatBlock.objects.create(
             slug='tmpl_block',
             header='{{ header_variable }}',
             content='{{ variable }}'
        )
        tpl = template.Template('{% load flatblock_tags %}{% flatblock "tmpl_block" evaluated %}')
        result = tpl.render(template.Context({
            'variable': 'value',
            'header_variable': 'header-value'
        }))
        self.assertTrue('header-value' in result)


class AutoCreationTest(TestCase):
    """ Test case for block autcreation """

    def testMissingStaticBlock(self):
        """Tests if a missing block with hardcoded name will be auto-created"""
        expected = """<div class="flatblock block-foo">

    <div class="content">foo</div>
</div>"""
        settings.AUTOCREATE_STATIC_BLOCKS = True
        tpl = template.Template('{% load flatblock_tags %}{% flatblock "foo" %}')
        self.assertEqual(expected, tpl.render(template.Context({})).strip())
        self.assertEqual(FlatBlock.objects.count(), 1)
        self.assertEqual(expected, tpl.render(template.Context({})).strip())
        self.assertEqual(FlatBlock.objects.count(), 1)

    def testNotAutocreatedMissingStaticBlock(self):
        """Tests if a missing block with hardcoded name won't be auto-created if feature is disabled"""
        expected = u""
        settings.AUTOCREATE_STATIC_BLOCKS = False
        tpl = template.Template('{% load flatblock_tags %}{% flatblock "block" %}')
        self.assertEqual(expected, tpl.render(template.Context({})).strip())
        self.assertEqual(FlatBlock.objects.filter(slug='block').count(), 0)

    def testMissingVariableBlock(self):
        settings.AUTOCREATE_STATIC_BLOCKS = True
        """Tests if a missing block with variable name will simply return an empty string"""
        tpl = template.Template('{% load flatblock_tags %}{% flatblock name %}')
        self.assertEqual('', tpl.render(template.Context({'name': 'foo'})).strip())


