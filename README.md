# Felidetect
The Big Cat Vocalization Detection and Classification system is being developed to provide a user-friendly interface that enables non-technical users to easily extract, visualize, and analyze big cat vocal sounds, specifically focusing on endangered species like the Amur leopard.

## Purpose/ End Goal:

In efforts to conserve endangered species such as the Amur leopard, tracking reproductive cycles is crucial. Current methods for monitoring reproductive cycles and animal behavior, such as hormonal and fecal analysis, are both expensive and time-consuming, often taking months to yield results. Due to the solitary nature of these animals and the challenges of obtaining vaginal swabs, conservationists have turned to vocalization analysis. Additionally, the manual analysis of large audio datasets requires technical expertise, making it difficult for non-technical users to accurately study vocal behavior and reproductive patterns over time. The Big Cat Vocalization Detection and Classification system is being developed to address these challenges by providing a user-friendly interface that enables non-technical users to easily extract, visualize, and analyze big cat vocal sounds, specifically focusing on endangered species like the Amur leopard.

Through automated tasks like noise reduction, SAW CALL detection, and frequency analysis using spectrograms, the system will improve research efficiency and conservation efforts. By leveraging vocalization patterns to track reproductive cycles and monitor animal communication and health, this tool will play a critical role in advancing conservation strategies for endangered big cat species. By monitoring vocal patterns, specifically the frequency of SAW CALLS, it is possible to determine when a female may be in heat. This method presents a non-invasive and timely alternative to track reproductive behavior in big cats.


## Version/Prototype 1:
This is our first version of the Felidetect system. It is an algorithm that takes an Original .wav audio file from a Google Drive folder, reduces it, and detects noise based on certain thresholds. It doesn't save these back in Google Drive and isn't automated. No Front End was created. 

## Version/Prototype 2: 
**Updated Code from 09/09/2024 to 10/12/24**
All Back End Code. Takes 1-hour original Audio Files, Reduces the noise, and creates a new 'reduced audio file', creates a new 1-4 second long audio file for each detected noise based on a certain threshold, Testing ways to put all this data into an Excel sheet to visualize information better. Started working on a function where the user can then verify each detected noise by viewing its Waveform, Spectrogram, and Audio to confirm if it's a SAW, SAW CALL, or Neither.

## Version/Prototype 3: 
**Updated Code from 10/12/2024 to 12/04/24**
All Back End Code. Takes 1-hour original Audio Files, Reduces the noise and creates a new 'reduced audio file', creates a new 1-4 second long audio file for each detected noises based on a certain threshold, puts all this data into an Excel sheet to visualize information better, user can then verify each detected noise by viewing it's Waveform, Spectrogram, and Audio to confirm if it's a SAW, SAW CALL, or Neither. After the user verifies each detection it updates the Excel sheet.
