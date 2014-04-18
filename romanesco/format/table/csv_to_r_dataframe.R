output<-read.csv(text=input, check.names=FALSE)

# If first column contains unique values, set the row names
if (anyDuplicated(output[,1]) == 0) {
    row.names(output)<-output[,1]
}