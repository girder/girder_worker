output<-read.csv(text=input, check.names=FALSE)
row.names(output)<-output[,1]
