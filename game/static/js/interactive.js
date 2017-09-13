var $game = {
    transactions: []
};

function updateAlert(element, state, old_state, id, out){
    element.classList.remove('alert-success');
    element.classList.remove('alert-danger');
    element.classList.remove('alert-dark');
    switch(state){
        case 0:
            element.classList.add('alert-dark');
            break;
        case 1:
        case 2:
            element.classList.add('alert-success');
            break;
        case 3:
            element.classList.add('alert-danger');
    }
    if(old_state === 0 && state !== 0 && !out){
        var btns = element.getElementsByTagName('button');
        var l = btns.length;
        for(var i=0; i<l; i++){
            btns[0].parentNode.removeChild(btns[0]);
        }
    }
    if(state === 0 && old_state !== 0 && !out){
        var accept = document.createElement('button');
        accept.classList.add('btn');
        accept.classList.add('btn-success');
        accept.appendChild(document.createTextNode('Принять'));
        accept.addEventListener('click', getHandler(acceptTransaction, [id]));
        var reject = document.createElement('button');
        reject.classList.add('btn');
        reject.classList.add('btn-danger');
        reject.appendChild(document.createTextNode('Отклонить'));
        reject.addEventListener('click', getHandler(rejectTransaction, [id]));
        element.appendChild(reject);
        element.appendChild(accept);
    }
}

function acceptTransaction(id){
    updateAlert($game.transactions[id].element, 1, $game.transactions[id].state, id);
    $game.transactions[id].state = 1;
    backgroundRequest('GET', 'transactions/' + id + '/accept');
}

function rejectTransaction(id){
    updateAlert($game.transactions[id].element, 3, $game.transactions[id].state, id);
    $game.transactions[id].state = 3;
    backgroundRequest('GET', 'transactions/' + id + '/reject');
}

function updateTransactions(transactions){
    transactions.sort(function(a, b){ return a.id - b.id });
    var t_id;
    for(var i=0; i<transactions.length; i++){
        t_id = transactions[i].id;
        if(t_id in $game.transactions){
            if(transactions[i].state !== $game.transactions[t_id]){
                var elem = $game.transactions[t_id].element;
                updateAlert(elem, transactions[i].state, $game.transactions[t_id].state, t_id, transactions[i].out);
                $game.transactions[t_id].state = transactions[i].state;
            }
        }else{
            var alert = document.createElement('div');
            alert.classList.add('alert');
            alert.appendChild(document.createTextNode(transactions[i].text));
            updateAlert(alert, transactions[i].state, 3, t_id, transactions[i].out);

            document.getElementById('transactions').appendChild(alert);
            $game.transactions[t_id] = {state: transactions[i].state, text: transactions[i].text, element: alert};
        }
    }
}

function backgroundRequest(method, endpoint, callback, body){
    var xhr = new XMLHttpRequest();
    xhr.open(method, window.location.pathname + '/' + endpoint, true);
    xhr.send(body);
    xhr.onreadystatechange = function(){
        if(xhr.readyState !== 4) return;
        if(xhr.status !== 200){
            console.warn(xhr.status, method, endpoint, xhr.responseText);
            return;
        }
        if(callback) callback(xhr.responseText);
    }
}

function updateGame(raw_text){
    var data = JSON.parse(raw_text);
    updateTransactions(data.transactions);
    document.getElementById('p-money').innerHTML = data.money + ' GC';
    if(data.experience !== undefined) document.getElementById('p-exp').innerHTML = data.experience;
    if(data.tech !== undefined) document.getElementById('p-tech').innerHTML = data.tech;
    if(data.fame !== undefined) document.getElementById('p-fame').innerHTML = data.fame;
    if(data.part !== undefined) document.getElementById('p-part').innerHTML = data.part + '%';
    //TODO
}

function stopBackground(){
    clearInterval($game.updater);
}

function getHandler(func, args){
    return function(){
        func.apply(func, args);
    };
}

window.addEventListener('load', function(){
    backgroundRequest('GET', 'state', updateGame);
    $game.updater = setInterval(backgroundRequest, 8000, 'GET', 'state', updateGame);  // 8 sec
});