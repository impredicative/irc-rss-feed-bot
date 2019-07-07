URL = 'https://old.reddit.com/r/MachineLearning/hot/'
HEXT = """
<div class="midcol unvoted"><div class="score unvoted" title=~"\d\d\d" title:score></div></div>
<div class="entry unvoted"><div class="top-matter"><p class="title">
    <a class="title may-blank" href:replace(/^\/r\//, "https://reddit.com/r/"):link  @text:title />
</p></div></div>
"""
