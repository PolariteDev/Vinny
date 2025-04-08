/*
vinny - discord moderation bot
Copyright (C) 2024-2025 Polarograph

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

NOTE: If you wanna use my dashboard module without complying with above terms,
then contact me for inquiries/questions for permission. You will only be able to
use my commits if you have received permission from me. <0vfx@proton.me>
*/

function deleteSessionCookie() {
	document.cookie = "session=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
}

var userModal = document.getElementById("userModal");

function openModalAtPosition(element) {
	var rect = element.getBoundingClientRect();
	var left = rect.left + window.scrollX;
	var top = rect.top + window.scrollY;

	var modalWidth = userModal.offsetWidth;
	var modalHeight = userModal.offsetHeight;
	var windowHeight = window.innerHeight || document.documentElement.clientHeight;
	var windowWidth = window.innerWidth || document.documentElement.clientWidth;

	var finalLeft = Math.max(left, Math.min(windowWidth - modalWidth - 10, left));
	var finalTop = Math.max(top, Math.min(windowHeight - modalHeight - 10, top));

	userModal.style.left = `${finalLeft}px`;
	userModal.style.top = `${finalTop}px`;

	userModal.style.display = "block";
}

document.querySelectorAll('.userButton').forEach(function(button) {
	button.addEventListener('click', function() {
		openModalAtPosition(this);
	});
});

document.querySelector(".close").onclick = function() {
	userModal.style.display = "none";
}