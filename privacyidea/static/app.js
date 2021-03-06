/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2015-01-11 Cornelius Kölbel, <cornelius@privacyidea.org>
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */
myApp = angular.module("privacyideaApp",
    ['ui.router', 'ui.bootstrap', 'TokenModule',
        'ngAnimate', 'ngIdle',
        'privacyideaAuth',
        'privacyideaApp.auditStates',
        'privacyideaApp.configStates',
        'privacyideaApp.tokenStates',
        'privacyideaApp.userStates',
        'privacyideaApp.machineStates',
        'privacyideaApp.loginStates',
    'multi-select', 'angularFileUpload']);
myApp.config(function ($urlRouterProvider) {
    // For any unmatched url, redirect to /token
    $urlRouterProvider.otherwise("/token/list");
});
myApp.config(['KeepaliveProvider', 'IdleProvider',
    function (KeepaliveProvider, IdleProvider) {
    // Logout configuration
    IdleProvider.idle(20);
    IdleProvider.timeout(10);
    KeepaliveProvider.interval(3);
}]);

var instance = window.location.pathname;
if (instance === "/") {
    instance = "";
}
var backendUrl = "";
myApp.constant("instanceUrl", instance);
myApp.constant("authUrl", backendUrl + instance + "/auth");
myApp.constant("tokenUrl", backendUrl + instance + "/token");
myApp.constant("userUrl", backendUrl + instance + "/user");
myApp.constant("resolverUrl", backendUrl + instance + "/resolver");
myApp.constant("machineResolverUrl", backendUrl + instance + "/machineresolver");
myApp.constant("machineUrl", backendUrl + instance + "/machine");
myApp.constant("applicationUrl", backendUrl + instance + "/application");
myApp.constant("realmUrl", backendUrl + instance + "/realm");
myApp.constant("defaultRealmUrl", backendUrl + instance + "/defaultrealm");
myApp.constant("validateUrl", backendUrl + instance + "/validate");
myApp.constant("systemUrl", backendUrl + instance + "/system");
myApp.constant("auditUrl", backendUrl + instance + "/audit");
myApp.constant("policyUrl", backendUrl + instance + "/policy");
myApp.constant("CAConnectorUrl", backendUrl + instance + "/caconnector");
myApp.run(['$rootScope', '$state', '$stateParams',
        function ($rootScope, $state, $stateParams) {

            // It's very handy to add references to $state and $stateParams to the $rootScope
            // so that you can access them from any scope within your applications.For example,
            // <li ng-class="{ active: $state.includes('contacts.list') }"> will set the <li>
            // to active whenever 'contacts.list' or one of its decendents is active.
            $rootScope.$state = $state;
            $rootScope.$stateParams = $stateParams;
        }
    ]
);
myApp.config(['$httpProvider', function ($httpProvider) {
    $httpProvider.interceptors.push(function ($q) {
        return {
            responseError: function (rejection) {
                if(rejection.status === 0) {
                    // The API is offline, not reachable
                    addError("The privacyIDEA system seems to be offline. The API is not reachable!");
                    return;
                }
                return $q.reject(rejection);
            }
        };
    });

}]);

myApp.config(['$compileProvider',
    function ($compileProvider) {
        $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto|tel|file|blob):/);
}]);


function addError(message, wait) {
    if (!wait) {
        wait = 15000;
    }
    $('#alerts').append(
        '<div class="alert alert-danger">' +
            '<button type="button" class="close" data-dismiss="alert">' +
            '&times;</button>' + message + '</div>');
    setTimeout(function(){
        $('#alerts').children('.alert:first-child').remove();
    }, wait);
}

function addInfo(message, wait) {
    if (!wait) {
        wait = 5000;
    }
    $('#alerts').append(
        '<div class="alert alert-info">' +
            '<button type="button" class="close" data-dismiss="alert">' +
            '&times;</button>' + message + '</div>');
    setTimeout(function(){
        $('#alerts').children('.alert:first-child').remove();
    }, wait);
}
