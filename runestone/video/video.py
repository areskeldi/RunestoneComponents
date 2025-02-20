# Copyright (C) 2011  Bradley N. Miller
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
#
__author__ = "bmiller"

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst import Directive
from runestone.server.componentdb import addQuestionToDB, addHTMLToDB
from runestone.common.runestonedirective import (
    RunestoneIdDirective,
    RunestoneDirective,
    RunestoneIdNode,
)


def setup(app):
    app.add_directive("video", Video)
    app.add_directive("youtube", Youtube)
    app.add_directive("vimeo", Vimeo)
    app.add_node(VideoNode, html=(visit_video_node, depart_video_node))


CODE = """\
<div id="%(divid)s" class="video_popup runestone" >
<video %(controls)s %(preload)s %(loop)s poster="%(thumb)s">
    %(sources)s
    No supported video types
</video>
</div>
"""

POPUP = """\
<a id="%(divid)s_thumb" style='position:relative;'>
    <img src="%(thumb)s" />
    <div class='video-play-overlay'></div>
</a>
<script>
  window.addEventListener('load', (event) => {
    jQuery(function ($) {
       $('#%(divid)s_thumb').click(function (e) {
                $('#%(divid)s').modal();
                return false;
        });
    });
  });
</script>

"""

INLINE = """\
<script>
  window.addEventListener('load', (event) => {
    jQuery(function($) {
        var rb = new RunestoneBase();
        $('#%(divid)s_thumb').click(function(e) {
            $('#%(divid)s').show();
            $('#%(divid)s_thumb').hide();
            rb.logBookEvent({'event':'video','act':'play','div_id': '%(divid)s'});
            // Log the run event
        });
        $('#%(divid)s video').one("click", function(){
            this.play();
        });
        $('#%(divid)s video').one("play", function(){
            rb.logBookEvent({'event':'video','act':'play','div_id': '%(divid)s'});
        });
    });
  });
</script>
"""
SOURCE = """<source src="%s" type="video/%s"></source>"""


class VideoNode(nodes.General, nodes.Element, RunestoneIdNode):
    def __init__(self, content, **kwargs):
        super().__init__(**kwargs)
        self.runestone_options = content
        self.template = kwargs["template"]


def visit_video_node(self, node):
    html = node.template % node.runestone_options
    self.body.append(html)
    addHTMLToDB(
        node.runestone_options["divid"], node.runestone_options["basecourse"], html
    )


def depart_video_node(self, node):
    pass


class Video(RunestoneIdDirective):
    """
.. video:: id
   :controls:  Show the controls or not
   :loop: loop the video
   :thumb: url to thumbnail image
   :preload: set the video to preload in the bg

   url to video format 1
   url to video format 2
   ...
    """

    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = True
    option_spec = RunestoneIdDirective.option_spec.copy()
    option_spec.update(
        {
            "controls": directives.flag,
            "loop": directives.flag,
            "thumb": directives.uri,
            "preload": directives.flag,
        }
    )

    def run(self):
        """
        process the video directive and generate html for output.
        :param self:
        :return:
        """
        super(Video, self).run()
        addQuestionToDB(self)

        mimeMap = {"mov": "mp4", "webm": "webm", "m4v": "m4v"}

        sources = [
            SOURCE % (directives.uri(line), mimeMap[line[line.rindex(".") + 1 :]])
            for line in self.content
        ]
        if "controls" in self.options:
            self.options["controls"] = "controls"
        if "loop" in self.options:
            self.options["loop"] = "loop"
        else:
            self.options["loop"] = ""

        if "preload" in self.options:
            self.options["preload"] = 'preload="auto"'
        else:
            self.options["preload"] = 'preload="none"'

        self.options["sources"] = "\n    ".join(sources)
        res = CODE % self.options
        if "popup" in self.options:
            res += POPUP % self.options
        else:
            res += INLINE % self.options

        addHTMLToDB(self.options["divid"], self.options["basecourse"], res)
        return [nodes.raw(self.block_text, res, format="html")]


"""
    ReST directive for embedding Youtube and Vimeo videos.

    There are two directives added: ``youtube`` and ``vimeo``. The only
    argument is the video id of the video to include.

    Both directives have four optional arguments: ``height``, ``width``
    and ``align``. Default height is 281 and default width is 500.
    The default transport is HTTP although HTTPS can be specified.

    Example::

        .. youtube:: anwy2MPT5RE
            :height: 315
            :width: 560
            :align: left
            :http: http

    :copyright: (c) 2012 by Danilo Bargen.
    :license: BSD 3-clause
"""


def align(argument):
    """Conversion function for the "align" option."""
    return directives.choice(argument, ("left", "center", "right"))


def httpOption(argument):
    """Conversion function for the "http" option."""
    return directives.choice(argument, ("http", "https"))


class IframeVideo(RunestoneIdDirective):
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = RunestoneIdDirective.option_spec.copy()
    option_spec.update(
        {
            "height": directives.nonnegative_int,
            "width": directives.nonnegative_int,
            "align": align,
            "http": httpOption,
            "divid": directives.unchanged,
        }
    )
    default_width = 500
    default_height = 281

    def run(self):
        super(IframeVideo, self).run()
        self.options["video_id"] = directives.uri(self.arguments[0])
        if not self.options.get("width"):
            self.options["width"] = self.default_width
        if not self.options.get("height"):
            self.options["height"] = self.default_height
        if not self.options.get("align"):
            self.options["align"] = "left"
        if not self.options.get("http"):
            self.options["http"] = "https"
        if not self.options.get("divid"):
            self.options["divid"] = self.arguments[0]

        # res = self.html % self.options
        # addHTMLToDB(self.options["divid"], self.options["basecourse"], res)
        raw_node = VideoNode(
            self.options, rawsource=self.block_text, template=self.html
        )
        # nodes.raw(self.block_text, res, format="html")
        raw_node.source, raw_node.line = self.state_machine.get_source_and_line(
            self.lineno
        )
        return [raw_node]


class Youtube(IframeVideo):
    """
.. youtube:: YouTubeID
   :divid: the runestone id for this video
   :height: 315
   :width: 560
   :align: left
   :http: http
   :start: None
   :end: None
   """

    html = """
    <div class="runestone" style="margin-left: auto; margin-right:auto">
        <div id="%(divid)s" data-component="youtube" class="align-%(align)s youtube-video"
            data-video-height="%(height)d" data-question_label="%(question_label)s"
            data-video-width="%(width)d" data-video-videoid="%(video_id)s"
            data-video-divid="%(divid)s" data-video-start="%(start)d"
            data-video-end="%(end)s" ></div>
    </div>
    """

    option_spec = IframeVideo.option_spec.copy()
    option_spec.update(
        {"start": directives.nonnegative_int, "end": directives.nonnegative_int}
    )

    def run(self):
        if not self.options.get("start"):
            self.options["start"] = 0

        if not self.options.get("end"):
            self.options["end"] = -1

        raw_node = super(Youtube, self).run()
        addQuestionToDB(self)
        return raw_node


class Vimeo(IframeVideo):
    """
.. vimeo:: vimeoID
   :height: 315
   :width: 560
   :align: left
   :http: http
    """

    html = '<iframe src="%(http)s://player.vimeo.com/video/%(video_id)s" \
    width="%(width)u" height="%(height)u" frameborder="0" \
    webkitAllowFullScreen mozallowfullscreen allowFullScreen \
    class="align-%(align)s" seamless ></iframe>'


source = """\
This is some text.

.. video:: divid
   :controls:
   :thumb: _static/turtlestill.png
   :loop:

   http://knuth.luther.edu/~bmiller/foo.mov
   http://knuth.luther.edu/~bmiller/foo.webm

This is some more text.
"""

if __name__ == "__main__":
    from docutils.core import publish_parts

    directives.register_directive("video", Video)

    doc_parts = publish_parts(
        source,
        settings_overrides={"output_encoding": "utf8", "initial_header_level": 2},
        writer_name="html",
    )

    print(doc_parts["html_body"])
