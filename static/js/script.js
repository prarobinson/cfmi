/* Author: Shawn Nock <nock@nocko.org> */

$().ready(function () {
    $(".button").hover(
	function () {
	    $(this).addClass("lit")
	},
	function () {
	    $(this).removeClass("lit")
	});
    $("#messages").hide().addClass("info");
});





















