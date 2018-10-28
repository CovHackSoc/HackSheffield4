/***** Colour chooser ********/

var currentColour = "s1"

$(document).ready(function(){
  $(".swatch").each(function(index) {
      var colour = $(this).data("colour");
      $(this).css("background-color", "#"+colour);
      if(this.id == currentColour) {
        $(this).addClass('swatch-selected')
        $('body').css('background-color', '#'+$(this).data("colour"))
      }
  });
});


function nextColour() {
  switch(currentColour) {
    case "s1":
      currentColour = "s2"
      break;
    case "s2":
      currentColour = "s3"
      break;
    case "s3":
      currentColour = "s4"
      break;
    case "s4":
      currentColour = "s5"
      break;
    case "s5":
      currentColour = "s6"
      break;
    case "s6":
      currentColour = "s1"
      break;
  }

  $(".swatch").each(function(index) {
      if(this.id == currentColour) {
        $(this).addClass('swatch-selected')
        var colourToSend = $(this).data("colour")
        $('body').css('background-color', '#'+colourToSend);
        const payload = '{"command":"colour","data":"'+colourToSend+'"}'
        publish(payload,'HackShef/bobro',2)
      } else {
        $(this).removeClass('swatch-selected')
      }
  });

}

/***** Leap ********/
var timer = (new Date()).getTime();
var timer1 = (new Date()).getTime();

var brushDown = false

// Store frame for motion functions
var previousFrameRoll = null;
var controllerOptions = {enableGestures: true};

var frameString = 0
var pos = 0

var gestureString = ""

function getHandRollInDegs(frame) {
  if(frame.hands.length > 0) {
    return frame.hands[0].roll() * (180 / Math.PI)
  }
}

var rotation = 0

Leap.loop(controllerOptions, function(frame) {

  if(frame.hands.length > 0) {
    if(brushDown !== true) {
      console.log('DOWN')
      brushDown = true
      const payload = '{"command":"brushDown","data":""}'
      publish(payload,'HackShef/bobro',2)
    }
  } else {
    if(brushDown === true) {
      console.log('UP')
      brushDown = false
      const payload = '{"command":"brushUp","data":""}'
      publish(payload,'HackShef/bobro',2)
    }
  }

  if(frame.hands.length == 2 && frame.hands[0].confidence > 0.8 && frame.hands[1].confidence > 0.8) {
    if (frame.hands[0].grabStrength < 0.1 && frame.hands[1].grabStrength < 0.1) {
      if(((new Date()).getTime() - timer1) > 5000) {
        console.log("SAVE")
        $('#save-flash').show()
        const payload = '{"command":"save","data":""}'
        publish(payload,'HackShef/bobro',2)
        timer1 = (new Date()).getTime()
        setTimeout(function(){
          $('#save-flash').hide()
        }, 2000);
      }


    }
  }

  if (frame.gestures.length > 0) {
    gestureString = ""
    for (var i = 0; i < frame.gestures.length; i++) {
      var gesture = frame.gestures[i];

      switch (gesture.type) {
        case "circle":
          gestureString = ".";
          if(gesture.state == "stop") {

            console.log(timer)
            console.log((new Date()).getTime())
            if(((new Date()).getTime() - timer) > 1000) {
              nextColour()
              timer = (new Date()).getTime()
            }


          }
          console.log(gesture.state)
          break;
        default:
          gestureString += "unkown gesture type";
      }
    }
  }

  //document.getElementById("frameData").innerHTML = "<div style='width:300px; float:left; padding:5px'>" + gestureString + "</div>";

})


/**** MQTT *****/

const client = new Messaging.Client('broker.mqttdashboard.com', 8000, `myclientid_${parseInt(Math.random() * 100, 10)}`)

const publish = (payload, topic, qos) => {
	const message = new Messaging.Message(payload)
	message.destinationName = topic
	message.qos = qos
	client.send(message)
}

const options = {
	timeout: 3,
	onSuccess: () => {
		console.log('connected')
		client.subscribe('HackShef/bobro', {qos: 2})
		console.log('Subscribed')
	},
	onFailure: message => console.log(`Connection failed: ${message.errorMessage}`)
}

client.connect(options)
